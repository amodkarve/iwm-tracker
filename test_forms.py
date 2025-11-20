"""
Simple Streamlit app to test form submission inside expanders
"""
import streamlit as st
from datetime import datetime

st.title("Form Submission Test")

st.markdown("## Test 1: Form Outside Expander")

with st.form("test_form_1"):
    name = st.text_input("Name", value="Test")
    submit1 = st.form_submit_button("Submit Form 1")
    
    if submit1:
        st.success(f"✅ Form 1 submitted! Name: {name}")
        st.write(f"Timestamp: {datetime.now()}")

st.markdown("## Test 2: Form Inside Expander")

with st.expander("Click to expand", expanded=True):
    with st.form("test_form_2"):
        name2 = st.text_input("Name 2", value="Test 2")
        submit2 = st.form_submit_button("Submit Form 2")
        
        if submit2:
            st.success(f"✅ Form 2 submitted! Name: {name2}")
            st.write(f"Timestamp: {datetime.now()}")

st.markdown("## Test 3: Multiple Forms in Expanders")

for i in range(3):
    with st.expander(f"Form {i+1}", expanded=(i==0)):
        with st.form(f"test_form_{i+3}"):
            val = st.number_input(f"Value {i+1}", value=i+1, key=f"val_{i}")
            submit = st.form_submit_button(f"Submit Form {i+3}")
            
            if submit:
                st.success(f"✅ Form {i+3} submitted! Value: {val}")
                st.write(f"Timestamp: {datetime.now()}")
