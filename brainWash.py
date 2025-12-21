import streamlit as st
from google import genai
import os

# משיכת המפתח מה-Secrets
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🛡️ בדיקת חיבור חסינת תקלות")

if not api_key:
    st.error("Missing API KEY in Secrets!")
else:
    try:
        client = genai.Client(api_key=api_key)
        
        if st.button("תלחץ כאן - אני מנסה הכל"):
            with st.spinner("מנסה ווריאציות שונות של המודל..."):
                
                # רשימת שמות מודלים אפשריים - ננסה אחד אחד
                possible_models = [
                    'gemini-1.5-flash',      # השם הסטנדרטי
                    'gemini-1.5-flash-001',  # גרסה ספציפית
                    'gemini-1.5-flash-8b',   # מודל קטן ומהיר עם פחות הגבלות
                    'gemini-2.0-flash'       # המודל החדש (למקרה שהמכסה שלו חזרה)
                ]
                
                success = False
                for model_name in possible_models:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents="Say 'Connection Established!'"
                        )
                        st.success(f"הצלחנו! המודל שענה הוא: {model_name}")
                        st.code(response.text)
                        st.balloons()
                        success = True
                        break # ברגע שאחד עובד, עוצרים
                    except Exception as e:
                        # אם נכשל, הוא עובר למודל הבא ברשימה
                        st.write(f"נסיתי את {model_name} וזה לא עבד... ממשיך לבא.")
                        continue
                
                if not success:
                    st.error("כל ניסיונות החיבור נכשלו. ייתכן שיש בעיה זמנית בשרתים של גוגל באזור שלך.")

    except Exception as e:
        st.error(f"שגיאה כללית: {e}")
