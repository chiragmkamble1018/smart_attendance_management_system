# app.py
import streamlit as st
from register import register_face
from verify import verify_attendance
from database import get_all_attendance, init_db # Import the required functions

st.title("🔐 Liveness-Verified Attendance System")

# Options list includes Register, Mark Attendance, and View Log
option = st.selectbox("Choose Action", ["Register New User", "✅ Mark Attendance", "📋 View Attendance Log"])

if option == "Register New User":
    name = st.text_input("Enter Full Name")
    if st.button("Start Registration (Blink Twice)"):
        if not name.strip():
            st.error("Please enter a name.")
        else:
            init_db() # Initialize DB
            with st.spinner("Opening camera... Please blink twice in the pop-up window."):
                success, message = register_face(name.strip())
                if success:
                    st.success(message)
                else:
                    # This catches the SPOOF DETECTED error message from register.py
                    st.error(message) 

elif option == "✅ Mark Attendance":
    if st.button("Start Verification (Blink Twice)"):
        init_db() # Initialize DB
        with st.spinner("Verifying liveness and identity..."):
            # verify_attendance handles the camera and console output for verification result
            verify_attendance() 
        st.info("Verification process finished. Check your console for the full result, or view the log below.")

# LOGIC: Display log directly on the Streamlit frontend
elif option == "📋 View Attendance Log":
    st.header("Attendance Log")
    try:
        attendance_records = get_all_attendance() # Fetch data
        if attendance_records:
            # Convert the list of sqlite3.Row objects to a list of dicts for clean display
            data = [dict(row) for row in attendance_records]
            
            # Use Streamlit's dataframe to display the log
            st.dataframe(data, 
                         column_order=("timestamp", "name", "verified"),
                         column_config={
                             "timestamp": st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD HH:mm:ss"),
                             "name": "User Name",
                             "verified": "Verification Status"
                         },
                         use_container_width=True)
        else:
            st.info("No attendance records have been marked yet.")
            
    except Exception as e:
        st.error(f"Error fetching attendance log: {e}")