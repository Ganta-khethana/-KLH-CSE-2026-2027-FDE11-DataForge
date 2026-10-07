import streamlit as st
import pandas as pd
import random
import plotly.express as px

# Movie data
movie_names = [f"Movie {i}" for i in range(1, 101)]

directors = [
    "Christopher Nolan",
    "Steven Spielberg",
    "Quentin Tarantino",
    "James Cameron",
    "Martin Scorsese"
]

heroes = [
    "Leonardo DiCaprio",
    "Tom Cruise",
    "Brad Pitt",
    "Robert Downey Jr.",
    "Chris Evans"
]

heroines = [
    "Scarlett Johansson",
    "Emma Watson",
    "Natalie Portman",
    "Anne Hathaway",
    "Jennifer Lawrence"
]

producers = [
    "Warner Bros",
    "Universal",
    "Paramount",
    "Sony Pictures",
    "20th Century Studios"
]

# Generate data
data = {
    "Movie Name": [random.choice(movie_names) for _ in range(100)],
    "Director": [random.choice(directors) for _ in range(100)],
    "Total Collection ($M)": [random.randint(50, 2000) for _ in range(100)],
    "Rating": [round(random.uniform(5.0, 9.9), 1) for _ in range(100)],
    "Budget ($M)": [random.randint(10, 500) for _ in range(100)],
    "Hero": [random.choice(heroes) for _ in range(100)],
    "Heroine": [random.choice(heroines) for _ in range(100)],
    "Producer": [random.choice(producers) for _ in range(100)]
}

df = pd.DataFrame(data)

# Page settings
st.set_page_config(
    page_title="Movies Dashboard",
    layout="wide"
)

st.title("🎬 Movie Analytics Dashboard")

st.write(
    "Explore movies, ratings, budgets and box-office collections."
)

# Sidebar
st.sidebar.header("🔍 Filter Options")

selected_director = st.sidebar.selectbox(
    "🎬 Choose Director",
    ["All"] + directors
)

selected_hero = st.sidebar.selectbox(
    "🦸 Choose Hero",
    ["All"] + heroes
)

selected_heroine = st.sidebar.selectbox(
    "💃 Choose Heroine",
    ["All"] + heroines
)

rating_range = st.sidebar.slider(
    "⭐ Rating Range",
    5.0,
    10.0,
    (5.0, 10.0),
    0.1
)

# Filtering
filtered_df = df.copy()

if selected_director != "All":
    filtered_df = filtered_df[
        filtered_df["Director"] == selected_director
    ]

if selected_hero != "All":
    filtered_df = filtered_df[
        filtered_df["Hero"] == selected_hero
    ]

if selected_heroine != "All":
    filtered_df = filtered_df[
        filtered_df["Heroine"] == selected_heroine
    ]

filtered_df = filtered_df[
    (filtered_df["Rating"] >= rating_range[0]) &
    (filtered_df["Rating"] <= rating_range[1])
]

# Display data
st.subheader("📋 Filtered Movie Data")
st.dataframe(filtered_df, use_container_width=True)

# Statistics
st.subheader("📈 Summary Statistics")
st.write(filtered_df.describe())

# Charts
col1, col2 = st.columns(2)

with col1:

    st.subheader("💰 Collection vs Budget")

    fig1 = px.scatter(
        filtered_df,
        x="Budget ($M)",
        y="Total Collection ($M)",
        color="Director",
        size="Rating",
        hover_data=[
            "Movie Name",
            "Hero",
            "Heroine"
        ],
        title="Budget vs Box Office Collection"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

with col2:

    st.subheader("⭐ Rating Distribution")

    fig2 = px.histogram(
        filtered_df,
        x="Rating",
        nbins=20,
        color="Director",
        title="Distribution of Movie Ratings"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# Top movies
st.subheader("🏆 Top 10 Highest Grossing Movies")

top_movies = filtered_df.sort_values(
    by="Total Collection ($M)",
    ascending=False
).head(10)

st.table(
    top_movies[
        [
            "Movie Name",
            "Director",
            "Total Collection ($M)",
            "Rating"
        ]
    ]
)