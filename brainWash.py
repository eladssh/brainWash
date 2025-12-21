import streamlit as st
from google import genai
import os

# 1. ניסיון למשוך את המפתח מה-Secrets של Streamlit
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🔌 בדיקת חיבור ל-Gemini API")

if not api_key:
    st.error("המפתח (API KEY) חסר! וודא שהגדרת אותו ב-Secrets ב-Streamlit Cloud.")
    st.info("הפורמט ב-Secrets צריך להיות: GOOGLE_API_KEY = 'הקוד_שלך'")
else:
    st.success("המפתח זוהה במערכת. מנסה להתחבר למודל...")
    
    try:
        # 2. אתחול הלקוח של Gemini 2.0 (הגרסה היציבה והחדשה)
        client = genai.Client(api_key=api_key)
        
        if st.button("שלח הודעת בדיקה ל-AI"):
            with st.spinner("ממתין לתשובה מגוגל..."):
                # 3. קריאה פשוטה למודל
                response = client.models.generate_content(
                    model='gemini-1.5-flash', 
                    contents="האם אתה שומע אותי? תענה בקיצור: 'החיבור תקין!'"
                )
                
                st.subheader("תשובת ה-AI:")
                st.code(response.text)
                st.balloons()
                
    except Exception as e:
        st.error("נכשלו הניסיונות ליצור קשר עם ה-API.")
        st.exception(e) # זה ידפיס לנו בדיוק מה הבעיה אם תהיה כזו

