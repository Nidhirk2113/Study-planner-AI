# backend/gemini_client.py

import os
from typing import List, Dict
import google.generativeai as genai
from dotenv import load_dotenv
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv()
print("Gemini API key loaded:", os.getenv("GEMINI_API_KEY") is not None)

# function uses a query string and duckduckgo_search library to perform a web search
def perform_web_search(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    """Perform a DuckDuckGo search and return a list of results.
    Each result contains: title, href, body.
    """
    results: List[Dict[str, str]] = []
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                # result keys typically include: title, href, body
                if not isinstance(result, dict):
                    continue
                
                title = result.get('title') or ''
                href = result.get('href') or ''
                body = result.get('body') or ''
                
                if title and href:
                    results.append({
                        'title': title,
                        'href': href,
                        'body': body,
                    })
        
        return results
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return []

# A class that manages the interaction with the Gemini API and core agent logic
class GeminiClient:
    def __init__(self):
        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.chat = self.model.start_chat(history=[])
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            self.chat = None
    
    def generate_study_plan(self, topic: str) -> str:
        """Generate a structured study plan in HTML table format"""
        try:
            study_plan_prompt = f"""
You are an AI-powered study planner. Generate a study plan for the topic: "{topic}"

CRITICAL REQUIREMENTS:
- Output ONLY a valid HTML <table> element
- Use <tr>, <th>, and <td> elements
- NO markdown formatting, asterisks, or plain text separators
- NO text outside the table tags
- Table must have 4 columns: Topic | Resources | What You'll Learn | Hours of Learning

CONTENT REQUIREMENTS:
- Break "{topic}" into exactly 4-6 meaningful subtopics
- For each subtopic provide:
  • Topic: Clear subtopic name
  • Resources: Specific books, courses, or websites (real resources)
  • What You'll Learn: 1-2 concise learning outcomes
  • Hours of Learning: Realistic study time (e.g., "3 hrs", "5 hrs")

EXAMPLE FORMAT (DO NOT COPY CONTENT):
<table>
<tr>
<th>Topic</th>
<th>Resources</th>
<th>What You'll Learn</th>
<th>Hours of Learning</th>
</tr>
<tr>
<td>Subtopic 1</td>
<td>Book Name, Online Course</td>
<td>Key skill, Core concept</td>
<td>4 hrs</td>
</tr>
</table>

Generate the study plan for: {topic}
"""
            
            if self.chat is None:
                return self._fallback_study_plan(topic)
            
            response = self.chat.send_message(study_plan_prompt)
            
            # Clean the response to ensure only table HTML is returned
            response_text = response.text.strip()
            
            # Extract only the table if there's extra text
            if '<table>' in response_text and '</table>' in response_text:
                start = response_text.find('<table>')
                end = response_text.find('</table>') + 8
                response_text = response_text[start:end]
            
            return response_text
            
        except Exception as e:
            print(f"Error generating study plan: {e}")
            return self._fallback_study_plan(topic)
    
    def _fallback_study_plan(self, topic: str) -> str:
        """Fallback study plan if API fails"""
        return f"""<table>
<tr>
<th>Topic</th>
<th>Resources</th>
<th>What You'll Learn</th>
<th>Hours of Learning</th>
</tr>
<tr>
<td>Foundations of {topic}</td>
<td>Online tutorials, Documentation</td>
<td>Basic concepts and terminology</td>
<td>3 hrs</td>
</tr>
<tr>
<td>Core Principles</td>
<td>Textbooks, Video courses</td>
<td>Fundamental principles and methods</td>
<td>5 hrs</td>
</tr>
<tr>
<td>Practical Application</td>
<td>Hands-on projects, Exercises</td>
<td>Real-world problem solving</td>
<td>4 hrs</td>
</tr>
<tr>
<td>Advanced Topics</td>
<td>Research papers, Expert blogs</td>
<td>Advanced techniques and best practices</td>
<td>6 hrs</td>
</tr>
</table>"""

    def generate_response(self, user_input: str) -> str:
        """Generate regular chat responses"""
        try:
            # Check if user is asking for search functionality
            text = user_input or ""
            lower = text.strip().lower()
            
            # Search trigger
            search_query = None
            if lower.startswith("search:"):
                search_query = text.split(":", 1)[1].strip()
            elif lower.startswith("/search "):
                search_query = text.split(" ", 1)[1].strip()
            
            if search_query:
                web_results = perform_web_search(search_query, max_results=6)
                
                if not web_results:
                    return "I could not retrieve web results right now. Please try again."
                
                # Build context with numbered references
                refs_lines = []
                for idx, item in enumerate(web_results, start=1):
                    refs_lines.append(f"[{idx}] {item['title']} — {item['href']}\n{item['body']}")
                
                refs_block = "\n\n".join(refs_lines)
                
                system_prompt = (
                    "You are an AI research assistant. Use the provided web search results to answer the user query. "
                    "Synthesize concisely, cite sources inline like [1], [2] where relevant, and include a brief summary."
                )
                
                composed = (
                    f"\n{system_prompt}\n\n"
                    f"Query: {search_query}\n\n"
                    f"Search Results:\n{refs_block}\n"
                )
                
                response = self.chat.send_message(composed)
                return response.text
            
            # Default: normal chat with study planner personality
            style_instructions = (
                "You are a friendly study planner AI assistant. "
                "Explain things in a structured but simple way, "
                "using headings, bullet points, and short paragraphs. "
                "Avoid long blocks of text. "
                "Use emojis occasionally to keep it engaging for students. "
                "If someone asks about creating a study plan, suggest they specify the topic they want to learn."
            )
            
            text_with_style = f"{style_instructions}\nUser: {user_input}"
            
            if self.chat is None:
                return "I'm sorry, I'm having trouble connecting right now. Please try again later."
            
            response = self.chat.send_message(text_with_style)
            return response.text
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error processing your request. Please try again."