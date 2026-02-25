import streamlit as st
import docx
from io import BytesIO
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

# --- AZURE CONFIGURATION ---
st.sidebar.title("Azure Language Service")
st.sidebar.info("Use the Language Service (Text Analytics) Key and Endpoint from Azure Portal.")
AZURE_KEY = st.sidebar.text_input("Enter Azure Language Key", type="password")
AZURE_ENDPOINT = st.sidebar.text_input("Enter Endpoint URL")

def get_language_client():
    return TextAnalyticsClient(
        endpoint=AZURE_ENDPOINT, 
        credential=AzureKeyCredential(AZURE_KEY)
    )

def read_docx(file):
    """Reads a .docx file and returns a list of non-empty paragraphs."""
    doc = docx.Document(file)
    return [para.text.strip() for para in doc.paragraphs if para.text.strip()]

def split_qa(lines):
    """
    Splits text based on simple heuristics.
    - Lines ending in '?' or labeled as 'User A' are treated as Questions.
    - Other lines are treated as Answers.
    """
    questions = []
    answers = []
    
    for line in lines:
        # Heuristic for detecting questions
        if line.endswith("?") or "User A:" in line or "Question:" in line:
            questions.append(line)
        else:
            answers.append(line)
            
    return "\n".join(questions), "\n".join(answers)

def summarize_with_azure(text_to_summarize):
    """Uses Azure Language Service Abstractive Summarization (v5.3.0+ method)."""
    if not text_to_summarize.strip():
        return "No answer text provided to summarize."
        
    client = get_language_client()
    
    try:
        # The method name is begin_abstract_summary in the stable 5.3.0 SDK
        poller = client.begin_abstract_summary([text_to_summarize])
        result = poller.result()
        
        summary_out = []
        for doc in result:
            if not doc.is_error:
                for summary in doc.summaries:
                    summary_out.append(summary.text)
            else:
                return f"Azure Service Error: {doc.error.message}"
                
        return " ".join(summary_out) if summary_out else "AI could not generate a summary."
    except Exception as e:
        return f"Logic Error: {str(e)}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="AI Conversation Analyzer", page_icon="🤖", layout="wide")

st.title(" AI Conversation: Q&A Splitter & Summarizer")
st.markdown("""
This tool uses **Azure AI Language** to process conversation transcripts. 
It separates questions from answers and uses Abstractive AI to summarize the responses.
""")

uploaded_file = st.file_uploader("Upload your Conversation Word File (.docx)", type=["docx"])

if uploaded_file and AZURE_KEY and AZURE_ENDPOINT:
    # 1. Read Document
    lines = read_docx(uploaded_file)
    
    if st.button("Analyze & Summarize Answers"):
        if not lines:
            st.error("The uploaded file appears to be empty.")
        else:
            with st.spinner("Azure AI is analyzing your conversation..."):
                try:
                    # 2. Split Logic
                    questions_txt, answers_txt = split_qa(lines)
                    
                    # 3. Azure Summarization
                    summary_txt = summarize_with_azure(answers_txt)
                    
                    # --- DISPLAY RESULTS ---
                    st.success(" Analysis Complete!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(" Extracted Questions")
                        st.text_area("Questions List", questions_txt, height=300)
                        st.download_button("Download Questions (.txt)", questions_txt, file_name="questions.txt")
                    
                    with col2:
                        st.subheader(" Extracted Answers")
                        st.text_area("Answers List", answers_txt, height=300)
                        st.download_button("Download Answers (.txt)", answers_txt, file_name="answers.txt")
                    
                    st.divider()
                    st.subheader(" AI-Generated Summary of Answers")
                    st.info(summary_txt)
                    st.download_button("Download Summary (.txt)", summary_txt, file_name="summary_final.txt")

                except Exception as e:
                    st.error(f"Critical Error: {e}")
else:
    if not (AZURE_KEY and AZURE_ENDPOINT):
        st.warning("Please enter your Azure Language Key and Endpoint in the sidebar.")
    else:
        st.info(" Please upload a .docx file to get started.")