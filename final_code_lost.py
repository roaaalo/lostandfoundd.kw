import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid

# --- Option Lists ---
TYPE_OPTIONS = ["Lost", "Found"]
CATEGORY_OPTIONS = ["Pets", "Electronics", "Bags", "Jewelry", "Personal Items", "Others"]
CITY_OPTIONS = ["Kuwait City", "Salmiya", "Hawally", "Jahra", "Farwaniya", "Ahmadi", "Mubarak Al-Kabeer"]

# --- File Config ---
DATA_FILE = "announcements.csv"
IMAGES_FOLDER = "announcement_images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# --- Data Handling ---
def load_data():
    columns = ["ID", "Type", "Category", "City", "Description",
               "Image1", "Image2", "Image3", "Phone", "Date",
               "EventDate", "DeletePassword", "Resolved"]
    if os.path.exists(DATA_FILE):
        # read everything as string to avoid dtype surprises, then normalize
        df = pd.read_csv(DATA_FILE, dtype=str)
        # ensure all expected columns exist
        for c in columns:
            if c not in df.columns:
                df[c] = ""
        # normalize types
        df["ID"] = df["ID"].fillna("").astype(str)
        df["DeletePassword"] = df["DeletePassword"].fillna("").astype(str)
        # Normalize Resolved to boolean
        df["Resolved"] = df["Resolved"].fillna("False").astype(str).str.lower().map({
            "true": True, "false": False, "1": True, "0": False
        }).fillna(False).astype(bool)
        # Ensure EventDate and Date exist as strings (ISO YYYY-MM-DD expected)
        df["EventDate"] = df["EventDate"].fillna("").astype(str)
        df["Date"] = df["Date"].fillna("").astype(str)
        # Keep only expected columns and return
        return df[columns]
    else:
        return pd.DataFrame(columns=columns)

def save_data(df):
    # save DataFrame to CSV
    df.to_csv(DATA_FILE, index=False)

def save_images(files):
    paths = []
    for file in files[:3]:
        if file is not None:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}_{file.name}"
            filepath = os.path.join(IMAGES_FOLDER, filename)
            with open(filepath, "wb") as f:
                f.write(file.getbuffer())
            paths.append(filepath)
    while len(paths) < 3:
        paths.append("")
    return paths

def try_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        # Streamlit may not expose experimental_rerun in some runtimes; ask user to refresh
        st.info("Please refresh manually to see changes.")

# --- Load Data ---
df = load_data()

# --- Sidebar Navigation ---
page = st.sidebar.radio("Navigate", ["🏠 Home", "📢 View Announcements"])

# ------------------- 🏠 Home Page -------------------
if page == "🏠 Home":
    st.header("Post a Lost or Found Item Announcement")

    post_type = st.radio("Type of item", TYPE_OPTIONS)
    category = st.selectbox("Category", CATEGORY_OPTIONS)
    city = st.selectbox("City / Area", CITY_OPTIONS)
    description = st.text_area("Description of the item")
    event_date = st.date_input(f"Date the item was {post_type.lower()}")
    phone = st.text_input("Contact Phone Number (8 digits)")
    delete_password = st.text_input("Set a delete password for this post", type="password")
    uploaded_files = st.file_uploader("Upload up to 3 pictures",
                                      type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if st.button("Submit Announcement"):
        if not description:
            st.error("Please enter a description.")
        elif len(phone) != 8 or not phone.isdigit():
            st.error("Phone number must be exactly 8 digits.")
        elif not delete_password:
            st.error("Please set a delete password.")
        else:
            image_paths = save_images(uploaded_files)
            # safe ID generation
            if df.empty:
                new_id = "1"
            else:
                try:
                    numeric_ids = pd.to_numeric(df["ID"], errors="coerce").dropna().astype(int)
                    if not numeric_ids.empty:
                        new_id = str(int(numeric_ids.max()) + 1)
                    else:
                        new_id = str(len(df) + 1)
                except Exception:
                    new_id = str(len(df) + 1)

            new_post = {
                "ID": new_id,
                "Type": post_type.lower(),
                "Category": category,
                "City": city,
                "Description": description,
                "Image1": image_paths[0],
                "Image2": image_paths[1],
                "Image3": image_paths[2],
                "Phone": phone,
                "Date": datetime.today().strftime("%Y-%m-%d"),
                "EventDate": event_date.strftime("%Y-%m-%d"),
                # strip whitespace to avoid accidental mismatches
                "DeletePassword": delete_password.strip(),
                "Resolved": False,
            }
            df = pd.concat([df, pd.DataFrame([new_post])], ignore_index=True)
            save_data(df)
            st.success("Announcement posted successfully!")

# ------------------- 📢 View Announcements -------------------
elif page == "📢 View Announcements":
    st.header("Lost & Found Announcements")

    # --- Basic Filters ---
    filter_type = st.selectbox("Filter by Type", ["All"] + TYPE_OPTIONS)
    filter_city = st.selectbox("Filter by City", ["All"] + CITY_OPTIONS)
    filter_category = st.selectbox("Filter by Category", ["All"] + CATEGORY_OPTIONS)
    show_resolved = st.checkbox("Include resolved announcements", value=False)

    # --- Date Filter Options ---
    st.markdown("### 🗓️ Optional Date Filters")
    date_filter_option = st.radio("Filter by:", ["No date filter", "Specific date", "Month and Year"])

    selected_date = None
    selected_month = None
    selected_year = None

    if date_filter_option == "Specific date":
        selected_date = st.date_input("Select a specific date")

    elif date_filter_option == "Month and Year":
        selected_month = st.selectbox("Month", list(range(1, 13)), format_func=lambda m: datetime(2023, m, 1).strftime('%B'))
        if not df.empty and "EventDate" in df.columns:
            # take years only from non-empty EventDate strings
            years = sorted(set(str(d)[:4] for d in df["EventDate"].dropna() if str(d).strip() != ""))
        else:
            years = [str(datetime.now().year)]
        selected_year = st.selectbox("Year", years)

    # --- Apply All Filters ---
    filtered = df.copy()
    if filter_type != "All":
        filtered = filtered[filtered["Type"] == filter_type.lower()]
    if filter_city != "All":
        filtered = filtered[filtered["City"] == filter_city]
    if filter_category != "All":
        filtered = filtered[filtered["Category"] == filter_category]
    if not show_resolved:
        filtered = filtered[filtered["Resolved"] == False]

    if date_filter_option == "Specific date" and selected_date:
        # FIXED: removed extra closing parenthesis
        filtered = filtered[filtered["EventDate"] == selected_date.strftime("%Y-%m-%d")]

    elif date_filter_option == "Month and Year" and selected_month and selected_year:
        # safe lambda to handle empty strings
        filtered = filtered[
            filtered["EventDate"].apply(
                lambda d: str(d)[:7] == f"{selected_year}-{str(selected_month).zfill(2)}"
            )
        ]

    # --- Display Results ---
    if filtered.empty:
        st.info("No announcements match the selected criteria.")
    else:
        # iterate newest first
        for idx, row in filtered[::-1].iterrows():
            st.markdown(f"### {'🔴 Lost' if str(row.get('Type','')).lower()=='lost' else '🟢 Found'} — {row.get('Category','')} in {row.get('City','')}")
            st.write(row.get("Description", ""))

            for img_col in ["Image1", "Image2", "Image3"]:
                img_path = row.get(img_col, "")
                if isinstance(img_path, str) and img_path.strip() != "" and os.path.exists(img_path):
                    st.image(img_path, width=300)

            st.write(f"📆 Date item was {row.get('Type','')}: {row.get('EventDate','')}")
            st.write(f"📅 Date posted: {row.get('Date','')}")
            st.write(f"📞 Contact: {row.get('Phone','')}")
            st.write(f"Status: {'✅ Resolved' if row.get('Resolved') else '❌ Unresolved'}")

            # --- Resolve Post ---
            if not row.get("Resolved"):
                with st.expander(f"Mark as Resolved — Post ID {row.get('ID')}"):
                    pw_resolve = st.text_input("Enter delete password to resolve this post",
                                               type="password", key=f"resolve_pw_{row.get('ID')}")
                    if st.button("Mark as Resolved", key=f"resolve_btn_{row.get('ID')}"):
                        # compare stripped strings
                        if str(pw_resolve).strip() == str(row.get("DeletePassword", "")).strip():
                            df.loc[df["ID"].astype(str) == str(row.get("ID")), "Resolved"] = True
                            save_data(df)
                            st.success("Post marked as resolved.")
                            try_rerun()
                        else:
                            st.error("Incorrect password.")

            # --- Delete Post ---
            with st.expander("Delete this announcement"):
                pw_delete = st.text_input("Enter delete password to delete this post",
                                          type="password", key=f"del_pw_{row.get('ID')}")
                if st.button("Delete Post", key=f"del_btn_{row.get('ID')}"):
                    # compare as stripped strings, robust to types
                    if str(pw_delete).strip() == str(row.get("DeletePassword", "")).strip() and str(pw_delete).strip() != "":
                        # remove from master df by ID (cast to str for safety)
                        df = df[df["ID"].astype(str) != str(row.get("ID"))]
                        save_data(df)
                        st.success("Post deleted successfully.")
                        try_rerun()
                    else:
                        st.error("Incorrect password.")

            st.markdown("---")