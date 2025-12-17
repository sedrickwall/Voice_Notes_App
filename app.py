from __future__ import annotations
import os
import tempfile
import streamlit as st

from utils.transcribe import transcribe_audio
from utils.openai_transcribe import transcribe_audio_openai
from utils.summarize import generate_notes
from utils.actions import extract_action_items
from utils.formatting import to_markdown
from utils.notion_export import export_to_notion_database
from utils.gdocs_export import export_to_google_doc

st.set_page_config(
    page_title="Voice Memo → Notes",
    page_icon="📝",
    layout="wide",
)

# --- Minimal responsive CSS for mobile friendliness ---
st.markdown("""
<style>
/* Reduce side padding on mobile */
@media (max-width: 768px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  h1 { font-size: 1.6rem; }
}
/* Make buttons full-width on small screens */
@media (max-width: 768px) {
  div.stButton > button { width: 100%; }
}
.small-label { font-size: 0.85rem; opacity: 0.8; }
.card {
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 14px;
  padding: 14px 16px;
  background: white;
}
</style>
""", unsafe_allow_html=True)

st.title("📝 Voice Memo → Notes")

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)

    colA, colB = st.columns([2, 1], gap="large")

    with colA:
        st.subheader("1) Upload audio")
        audio_file = st.file_uploader(
            "Upload a voice memo (m4a, mp3, wav)",
            type=["m4a", "mp3", "wav", "aac", "ogg"],
            label_visibility="collapsed",
        )

        title = st.text_input("Title", value="Voice Memo Notes")

    with colB:
        st.subheader("2) Settings")
        
        # Transcription method selector
        transcribe_method = st.radio(
            "Transcription method",
            ["Local (Faster-Whisper)", "OpenAI (Faster)"],
            help="Local: Free, slower. OpenAI: Faster, ~$0.012 per 2-hour file"
        )
        
        if transcribe_method == "OpenAI (Faster)":
            openai_key = st.text_input("OpenAI API Key", type="password", help="Get from https://platform.openai.com/api-keys")
        
        model_size = st.selectbox("Whisper model", ["tiny", "base", "small", "medium"], index=2)
        language = st.selectbox("Language", ["en", "auto"], index=0)
        st.caption("Tip: small is a great default. medium is slower but can be more accurate.")

    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# File size limit check
MAX_FILE_SIZE_MB = 50
if audio_file is not None and audio_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
    st.warning(f"⚠️ File is {audio_file.size / (1024*1024):.1f}MB. Recommended max: {MAX_FILE_SIZE_MB}MB. Processing may be slow or fail.")

generate = st.button("Generate Notes", type="primary", disabled=audio_file is None)

if generate and audio_file is not None:
    # Validate OpenAI key if using OpenAI method
    if transcribe_method == "OpenAI (Faster)" and not openai_key:
        st.error("Please provide your OpenAI API key")
        st.stop()
    
    with st.spinner("Processing audio…"):
        # Save uploaded file to temp
        suffix = os.path.splitext(audio_file.name)[1].lower() or ".m4a"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(temp_path, "wb") as f:
            f.write(audio_file.getbuffer())

        try:
            # Transcribe using selected method
            lang = None if language == "auto" else language
            
            if transcribe_method == "OpenAI (Faster)":
                transcript, detected_lang = transcribe_audio_openai(temp_path, api_key=openai_key, language=lang)
            else:
                transcript, detected_lang = transcribe_audio(temp_path, model_size=model_size, language=lang)
        except Exception as e:
            st.error(f"Transcription failed: {str(e)}")
            try:
                os.remove(temp_path)
            except Exception:
                pass
            st.stop()

        try:
            os.remove(temp_path)
        except Exception:
            pass

    if not transcript.strip():
        st.error("No transcript was produced. Try a clearer audio file or a larger model.")
        st.stop()

    notes = generate_notes(transcript)
    actions = extract_action_items(transcript)
    md = to_markdown(title=title, transcript=transcript, notes=notes, action_items=actions)

    st.success(f"Done. Detected language: {detected_lang}")

    # --- Results layout ---
    tab1, tab2, tab3 = st.tabs(["Notes", "Transcript", "Export"])

    with tab1:
        c1, c2 = st.columns([1, 1], gap="large")

        with c1:
            st.subheader("Summary")
            if notes["summary"]:
                for s in notes["summary"]:
                    st.write(f"• {s}")
            else:
                st.write("—")

            st.subheader("Key Points")
            if notes["key_points"]:
                for s in notes["key_points"]:
                    st.write(f"• {s}")
            else:
                st.write("—")

        with c2:
            st.subheader("Action Items")
            if actions:
                for a in actions:
                    st.write(f"☐ {a}")
            else:
                st.write("—")

            st.subheader("Questions")
            if notes["questions"]:
                for q in notes["questions"]:
                    st.write(f"• {q}")
            else:
                st.write("—")

        st.download_button(
            "Download as Markdown",
            data=md.encode("utf-8"),
            file_name=f"{title.replace(' ', '_').lower()}_notes.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with tab2:
        st.subheader("Full Transcript")
        st.text_area("Transcript", transcript, height=280, label_visibility="collapsed")

    with tab3:
        st.subheader("Export")

        with st.expander("Export to Notion", expanded=False):
            st.markdown('<div class="small-label">Requires a Notion integration token + a database shared with that integration.</div>', unsafe_allow_html=True)
            notion_token = st.text_input("Notion Token", type="password")
            notion_db = st.text_input("Notion Database ID")
            if st.button("Send to Notion", use_container_width=True):
                if not notion_token or not notion_db:
                    st.error("Please provide Notion Token and Database ID.")
                else:
                    try:
                        url = export_to_notion_database(
                            notion_token=notion_token,
                            database_id=notion_db,
                            title=title,
                            markdown_body=md,
                            action_items=actions,
                        )
                        if url:
                            st.success("Exported to Notion.")
                            st.markdown(f"[Open Notion page]({url})")
                        else:
                            st.warning("Exported, but no URL returned.")
                    except Exception as e:
                        st.error(f"Notion export failed: {e}")

        with st.expander("Export to Google Docs", expanded=False):
            st.markdown('<div class="small-label">Requires Google Docs API enabled + client_secret.json in the repo root.</div>', unsafe_allow_html=True)
            client_secret_path = st.text_input("Path to client_secret.json", value="client_secret.json")
            if st.button("Create Google Doc", use_container_width=True):
                if not os.path.exists(client_secret_path):
                    st.error(f"Could not find {client_secret_path}. Place your OAuth client file there.")
                else:
                    try:
                        url = export_to_google_doc(
                            client_secret_path=client_secret_path,
                            title=title,
                            markdown_body=md,
                        )
                        st.success("Created Google Doc.")
                        st.markdown(f"[Open Google Doc]({url})")
                    except Exception as e:
                        st.error(f"Google Docs export failed: {e}")
