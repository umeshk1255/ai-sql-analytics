# ask.py — AI SQL Agent using OpenAI GPT-4o-mini + SQLite + .env

import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from schemas import AskRequest, AskResponse

# 1️⃣ Load .env file
load_dotenv()

# 2️⃣ Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=api_key)

# 3️⃣ Connect to SQLite database
engine = create_engine("sqlite:///Chinook_Sqlite.sqlite")

# 4️⃣ Function to handle user query
def ask_database(question: str) -> AskResponse:
    try:
        # Step 1: Let GPT-4o-mini generate SQL
        prompt = f"""
        You are an expert SQL generator for the SQLite 'Chinook' database.
        Tables include: Artist, Album, Track, Customer, Invoice, and Genre.
        Convert the following user question into a valid SQL SELECT query.
        Return ONLY SQL code, no explanations or markdown.
        Question: {question}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful SQL assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        sql_query = response.choices[0].message.content.strip()
        print(f"🧠 GPT Generated SQL:\n{sql_query}\n")

        # Step 2: Safety check — only SELECT queries allowed
        if not sql_query.upper().startswith("SELECT"):
            return AskResponse(answer="❌ Only SELECT queries are allowed.")

        # Step 3: Execute query
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()

        # Step 4: Return formatted results
        if not rows:
            return AskResponse(answer="No results found.")

        formatted = [dict(row._mapping) for row in rows]
        return AskResponse(answer=json.dumps(formatted, indent=2))

    except SQLAlchemyError as e:
        print(f"❌ SQLAlchemy error: {e}")
        return AskResponse(answer=f"Database error: {str(e)}")
    except Exception as e:
        print(f"❌ General error: {e}")
        return AskResponse(answer=f"Error: {str(e)}")
