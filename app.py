# app.py

import streamlit as st
import uuid
from ragpipe import RAGPipeline

# --- Initialize pipeline ---
pipeline = RAGPipeline()

# --- Categorization logic ---
def categorize_ticket(text):
    text = text.lower()
    if "payment" in text or "deducted" in text:
        return "💳 Payment Issue"
    elif "return" in text:
        return "🔁 Return Request"
    elif "refund" in text:
        return "📉 Refund Issue"
    elif "shipping" in text or "order" in text or "delivered" in text:
        return "📦 Shipping Issue"
    else:
        return "❓ General Query"

if st.sidebar.button("🔁 Reset Ticket Embeddings"):
    pipeline.reset_support_tickets()
    st.sidebar.success("Support ticket vectors and logs have been cleared.")

st.markdown("### 📚 Upload Company Knowledge Document")
uploaded_file = st.file_uploader("Upload a .txt file (e.g., refund policy, shipping info)", type=["txt"])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    st.success(f"✅ `{uploaded_file.name}` uploaded and indexed.")
    pipeline.index_uploaded_kb(content, source_name=uploaded_file.name)

st.divider()

# --- UI ---
st.title("🧠 Smart Support Ticketing System")

ticket_text = st.text_area("Describe your issue:", height=150)

if st.button("Submit Ticket"):
    if ticket_text.strip() == "":
        st.warning("Please enter a message.")
    else:
        category = categorize_ticket(ticket_text)
        ticket_id = str(uuid.uuid4())
        st.success(f"✅ Ticket stored. Auto-categorized as: {category}")

        st.subheader("🔍 Similar Past Tickets:")
        similar = pipeline.search_similar(ticket_text)
        if similar["documents"] and similar["metadatas"]:
            for doc, meta in zip(similar["documents"][0], similar["metadatas"][0]):
                st.markdown(f"• _{doc}_  \n🗂️ Category: **{meta['category']}**")
        else:
            st.info("No similar tickets found in the database.")
        
        st.subheader("💬 Response:")
        response, score, is_confident = pipeline.generate_response(ticket_text)
        pipeline.store_ticket(ticket_id, ticket_text, category, response, score, is_confident)
        st.markdown(f"**{response}**")
        st.write(f"**Confidence Score:** {score:.2f}")
        st.write(f"**Is Confident:** {is_confident}")



st.divider()
st.markdown("### 🖥️ Agent Dashboard - Submitted Tickets")

if st.checkbox("📂 Show All Tickets"):
    tickets = pipeline.get_all_tickets()
    if not tickets:
        st.info("No tickets yet.")
    else:
        for t in tickets:
            with st.expander(f"🎫 Ticket: {t['text'][:50]}..."):
                st.markdown(f"**Category:** `{t['category']}`")
                st.markdown(f"**Confidence:** `{round(t['confidence'], 2)}`")
                st.markdown(f"**Escalation Needed?** {'⚠️ Yes' if t['escalate'] else '✅ No'}")
                st.markdown("**🤖 Suggested Response:**")
                st.markdown(t["response"])


