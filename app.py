def analyze_and_score(user_profile_text, internships):
    import cohere
    co = cohere.Client(COHERE_API_KEY)
    
    documents = []
    for internship in internships:
        job_text = f"{internship['title']} at {internship['company']} located in {internship['location']}. Description: {internship['description']} Salary Range: ${internship['salary_min']} - ${internship['salary_max']}"
        documents.append(job_text)

    try:
        response = co.rerank(
            model="rerank-english-v2.0",
            query=user_profile_text,
            documents=documents,
            top_n=len(documents)
        )

        scores = [0.0] * len(documents)
        for item in response.results:
            scores[item.index] = item.relevance_score

        # Normalize scores to between 0 and 1
        max_score = max(scores)
        if max_score > 0:
            scores = [score / max_score for score in scores]

        return scores

    except Exception as e:
        st.error(f"Rerank API error: {e}")
        return [0.0] * len(documents)

# Replace this part inside your main button logic:

if st.button("Find Matches"):
    internships_raw = fetch_internships("internship", location)
    internships = []
    for job in internships_raw:
        internships.append({
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "title": job.get("title", "Unknown Title"),
            "description": job.get("description", ""),
            "location": job.get("location", {}).get("display_name", "Unknown Location"),
            "salary_min": job.get("salary_min") or 0,
            "salary_max": job.get("salary_max") or 0,
        })

    user_inputs = {
        "gpa": gpa, "education": education, "school": school, "major": major,
        "skills": skills, "location": location, "industry": industry_preference,
        "org_type": org_type_preference, "schedule": schedule_preference,
        "salary_min": salary_min, "salary_max": salary_max,
        "start_date": start_date, "end_date": end_date
    }

    profile_text = create_user_profile_text(user_inputs, resume_text)
    st.write("\u2661 AI Matching in Progress...")

    scores = analyze_and_score(profile_text, internships)
    results = list(zip(scores, internships))
    results.sort(reverse=True, key=lambda x: x[0])

    st.subheader("\u2315 Top Matches:")
    for score, internship in results:
        st.markdown(f"**{internship['company']} - {internship['title']}**")
        st.write(f"Score: {score:.3f}")
        st.write(f"Location: {internship['location']}")
        st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
        with st.expander("Full Description"):
            st.write(internship['description'])
        st.write("---")

    G = nx.Graph()
    G.add_node("You")
    for score, internship in results[:50]:
        node = f"{internship['company']}\n{internship['title']}"
        G.add_node(node)
        G.add_edge("You", node, weight=score)
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")

    with open("graph.html", "r", encoding='utf-8') as HtmlFile:
        source_code = HtmlFile.read()
        components.html(source_code, height=650, width=900)
