import streamlit as st
import requests
from supabase import create_client, Client
import json
from datetime import datetime

# Page config
st.set_page_config(page_title="Scent Mood Matcher", page_icon="🕯️", layout="wide")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Fragrance notes database (simulating API)
FRAGRANCE_NOTES = {
    "relaxed": {
        "top": ["Lavender", "Chamomile", "Bergamot", "Sweet Orange"],
        "middle": ["Ylang Ylang", "Rose", "Jasmine", "Neroli"],
        "base": ["Sandalwood", "Vanilla", "Cedarwood", "Frankincense"]
    },
    "energized": {
        "top": ["Peppermint", "Eucalyptus", "Lemon", "Grapefruit"],
        "middle": ["Rosemary", "Basil", "Ginger", "Pine"],
        "base": ["Vetiver", "Patchouli", "Amber", "Musk"]
    },
    "romantic": {
        "top": ["Rose", "Peony", "Litchi", "Blackcurrant"],
        "middle": ["Jasmine", "Tuberose", "Magnolia", "Iris"],
        "base": ["Musk", "Amber", "Patchouli", "Vanilla"]
    }
}

def get_ai_recommendation(mood, notes, product_type):
    """Generate AI-powered recommendations using Google Gemini API"""
    
    prompt = f"""Based on a {mood} mood and these fragrance notes:
Top notes: {', '.join(notes['top'])}
Middle notes: {', '.join(notes['middle'])}
Base notes: {', '.join(notes['base'])}

Generate a creative {product_type} recommendation. Include:
1. A unique, marketable product name
2. A 2-3 sentence description highlighting the mood benefits
3. The perfect blend formula (percentages of each note)
4. Best time of day to use it

Respond ONLY with valid JSON in this exact format:
{{
  "name": "product name here",
  "description": "description here",
  "blend_formula": "formula here",
  "best_time": "time here"
}}"""

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={st.secrets['GEMINI_API_KEY']}",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            text_response = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response
            json_start = text_response.find("{")
            json_end = text_response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(text_response[json_start:json_end])
        return None
    except Exception as e:
        st.error(f"AI API Error: {str(e)}")
        return None

def save_to_supabase(data):
    """Save recommendation to Supabase"""
    try:
        result = supabase.table("fragrance_recommendations").insert({
            "mood": data["mood"],
            "product_type": data["product_type"],
            "product_name": data["name"],
            "description": data["description"],
            "blend_formula": data["blend_formula"],
            "best_time": data["best_time"],
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Database Error: {str(e)}")
        return False

# App Header
st.title("🕯️ Scent Mood Matcher")
st.markdown("### Discover your perfect fragrance blend powered by AI")

# Sidebar for inputs
with st.sidebar:
    st.header("Create Your Blend")
    
    mood = st.selectbox(
        "How do you want to feel?",
        ["relaxed", "energized", "romantic"],
        format_func=lambda x: x.capitalize()
    )
    
    product_type = st.radio(
        "What would you like to create?",
        ["candle", "body butter", "perfume blend"]
    )
    
    generate_btn = st.button("✨ Generate Recommendation", type="primary", use_container_width=True)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    if generate_btn:
        with st.spinner("🔮 Creating your personalized blend..."):
            # Get fragrance notes for the mood
            notes = FRAGRANCE_NOTES[mood]
            
            # Display the notes being used
            st.subheader("Fragrance Notes Selected")
            note_col1, note_col2, note_col3 = st.columns(3)
            with note_col1:
                st.markdown("**Top Notes**")
                for note in notes["top"]:
                    st.markdown(f"• {note}")
            with note_col2:
                st.markdown("**Middle Notes**")
                for note in notes["middle"]:
                    st.markdown(f"• {note}")
            with note_col3:
                st.markdown("**Base Notes**")
                for note in notes["base"]:
                    st.markdown(f"• {note}")
            
            # Get AI recommendation
            recommendation = get_ai_recommendation(mood, notes, product_type)
            
            if recommendation:
                st.success("✅ Recommendation Generated!")
                
                # Display recommendation
                st.markdown("---")
                st.subheader(f"🌟 {recommendation['name']}")
                st.markdown(recommendation['description'])
                
                st.markdown("**Blend Formula:**")
                st.info(recommendation['blend_formula'])
                
                st.markdown("**Best Time to Use:**")
                st.write(recommendation['best_time'])
                
                # Save to database
                data_to_save = {
                    "mood": mood,
                    "product_type": product_type,
                    **recommendation
                }
                
                if save_to_supabase(data_to_save):
                    st.success("💾 Saved to your collection!")
                    
                # Download button
                st.download_button(
                    label="📥 Download Recipe",
                    data=json.dumps(data_to_save, indent=2),
                    file_name=f"{recommendation['name'].replace(' ', '_')}.json",
                    mime="application/json"
                )

with col2:
    st.subheader("📊 Your History")
    
    try:
        # Fetch recent recommendations
        response = supabase.table("fragrance_recommendations").select("*").order("created_at", desc=True).limit(5).execute()
        
        if response.data:
            for item in response.data:
                with st.expander(f"{item['product_name']} ({item['mood']})"):
                    st.write(f"**Type:** {item['product_type']}")
                    st.write(f"**Created:** {item['created_at'][:10]}")
        else:
            st.info("No recommendations yet. Create your first blend!")
    except Exception as e:
        st.info("No recommendations yet. Create your first blend!")

# Footer
st.markdown("---")
st.markdown("*Powered by AI & Fragrance Science* 🌸")
