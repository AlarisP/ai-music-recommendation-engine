# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  
    MusicRecommender 1.0

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 
    This music recommender is designed to give users recommendations for what song to listen to next. It is for people who want a smooth music listening experience. It offers two scoring algorithms: a **simple** mode that is more data-driven and prioritizes genre and mood matching, and an **advanced** mode that groups features into emotional dimensions (FEEL, INTENSITY, STYLE, GROOVE) to create a continuous emotional thread through the music.

Prompts:  

- What kind of recommendations does it generate  
    It generates a ranked list of the top 5 songs that would be the best match to play next.
- What assumptions does it make about the user  
    It assumes the user wants songs that are similar to what they already know they like. It may introduce slightly different styles or moods through diversity penalties, but overall it stays close to the preferences the user has explicitly provided.
- Is this for real users or classroom exploration  
    This is for classroom exploration. To make it production-ready, I would need a database to store users and songs, an improved engine that accounts for other users' listening history (collaborative filtering), and a feedback loop so the system learns from what users actually play.

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
    The features used for each song are: genre, energy, mood, tempo (BPM), valence (how emotionally positive a song feels), danceability, and acousticness.
- What user preferences are considered  
    The user's preferred genre, mood, energy level, and whether they like acoustic music are all considered. Multiple favorite genres can also be ranked in order of preference.
- How does the model turn those into a score  
    In **simple mode**, the model adds up weighted points for each matching feature: genre is worth the most (×2), followed by mood (×1.5), energy (×1), and smaller bonuses for acoustic style and emotional tone (valence). The song with the highest total wins.  
    In **advanced mode**, features are grouped into four dimensions — FEEL (mood + valence), INTENSITY (energy + tempo), STYLE (acousticness + genre), and GROOVE (danceability) — and those groups are weighted together into a single score out of 1.0. A "mood gate" penalty then reduces the score of any song whose vibe is nearly the opposite of what the user wants, so a numerically close song can't sneak past a fundamentally wrong emotional fit. Both modes also apply small penalties for repeated artists and genres to keep the top-5 list diverse.
- What changes did you make from the starter logic  
    I added the advanced scoring mode described above, built out the FEEL/INTENSITY/STYLE/GROOVE grouping, implemented the mood gate penalty, and added diversity penalties for both artist and genre repetition. I also formatted the output as a table to make the recommendations easier to read at a glance.

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
    There are 19 songs total in the catalog.
- What genres or moods are represented  
    Genres: Pop, Rock, Lofi, Jazz, K-Pop  
    Moods: happy, sad, angry, chill, excited, intense, relaxed, moody, focused
- Did you add or remove data  
    I added data because there were not enough songs to give a clear picture of each song's character and to make meaningful comparisons between different users' tastes.
- Are there parts of musical taste missing in the dataset  
    I think language (e.g., lyrics in English vs. Korean vs. Spanish), content ratings, subgenres like death metal or bossa nova, and information about the emotional reputation of specific artists would all be helpful additions.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
    I would argue the output was reasonable for all five user profiles.
- Any patterns you think your scoring captures correctly  
    The persona that liked chill music (Alex) was spot-on, the jazz and lofi songs were scored well and the recommendations matched exactly what I would expect for that listener.
- Cases where the recommendations matched your intuition  
    Jordan, the rock persona, matched my intuition well. The system consistently chose harder, more passionate songs with high energy and intensity, which is exactly what that profile called for.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
    The system completely ignores what other similar users like (collaborative filtering), which is one of the most powerful signals in real recommenders. It also suffers from a small catalog and limited data variety.
- Genres or moods that are underrepresented 
    Subgenres are underrepresented — the catalog has broad labels like "rock" but no distinction between indie rock, metal, or classic rock, which are very different listening experiences.
- Cases where the system overfits to one preference 
    Because the catalog has more chill songs than any other vibe, users who prefer that style have more directly matching options available, while others have fewer good matches to choose from.
- Ways the scoring might unintentionally favor some users  
    Users at the emotional extremes (very happy or very sad, very intense or very chill) are served better because the system has clear signal to match against. Users with a blended or middle-of-the-road taste are harder to score accurately, since their preferences do not pull strongly toward any one cluster of songs.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
    I tested all 5 profiles. I ran all of them in simple mode and tested several in advanced mode as well.
- What you looked for in the recommendations  
    I looked for a clear rationale behind which songs were chosen, and for genre diversity within the top 5, especially in advanced mode, where the goal is the same emotional vibe but from a variety of artists and styles.
- What surprised you  
    I was surprised by how some of the same songs kept appearing across different users. I'm not sure whether that reflects genuine feature overlap in the catalog, or whether my own taste was unconsciously influencing how I judged which results were "correct."
- Any simple tests or comparisons you ran  
    I ran both scoring modes side by side on the same profiles and compared results — the recommended songs were similar but the reasoning differed in telling ways. I also created Riley, an intentionally contradictory profile (high energy + sad mood, EDM genre + likes acoustic), to see how the system handled a user it was never designed for.

No need for numeric metrics unless you created some.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
    I would incorporate data from other users, for example, a social following feature that lets users see what people they follow are listening to, which feeds into collaborative filtering.

    I would also add a Discover mode that intentionally surfaces songs outside the user's normal patterns but that they might still enjoy, to break out of the recommendation echo chamber.

    Blocking functionality so users can permanently remove a song or artist from their recommendations.
- Better ways to explain recommendations 
    Rather than showing the raw score calculation, I would replace it with a more human-readable explanation — something like "Because you loved the low-key jazz vibe of X, here's Y." The current explanation can be hard to parse for a non-technical user.
- Improving diversity among the top results  
    Expanding the diversity penalty to flag repeated subgenres and eras, not just repeated artists. Recommending four songs from the same era with the same production style is still repetitive even if the artists differ.
- Handling more complex user tastes  
    Adding finer-grained mood options and letting users set different "modes" for different situations (e.g., a workout mode vs. a focus mode) would better serve listeners whose tastes are contextual rather than fixed.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems 
    There is a lot that goes into them, and it can feel like more data always means better results. That does raise real concerns about user autonomy and where the line is between helpful personalization and intrusive surveillance.
- Something unexpected or interesting you discovered  
    I thought it was interesting how the five user profiles were designed to be distinct, yet I still saw some song overlap between users with only partially similar tastes, and users at the polar ends of the spectrum shared no songs at all.
- How this changed the way you think about music recommendation apps  
    It made me wonder just how much data streaming services actually collect and how precisely they use it, since they are essentially getting an unfiltered window into each person's emotional state over time.
