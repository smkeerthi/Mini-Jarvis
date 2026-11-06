"""
=============================================================================
MINI JARVIS - Intelligent AI Brain Module (brain.py)
=============================================================================
This module provides Jarvis with cognitive intelligence, allowing it to:
1. Answer general knowledge questions.
2. Solve math and logical problems.
3. Write, debug, and explain computer science code.
4. Explain academic concepts (DSA, Operating Systems, Networks, OOP).
5. Remember recent dialogue history to maintain multi-turn conversational context.

Architecture:
- Primary Engine: OpenAI-compatible LLM (OpenAI GPT-4o-mini, Groq Llama,
  OpenRouter, or local Ollama).
- Fallback Engine: Built-in Offline Knowledge Base & Pattern Responder.
  If the student doesn't have an API key or is offline, Jarvis still works
  smoothly and intelligently!
=============================================================================
"""

import os
import re
import logging
from typing import List, Dict, Optional
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    LLM_MODEL,
    JARVIS_SYSTEM_PROMPT
)
from database import db


class JarvisBrain:
    """Intelligent reasoning and conversational brain for Jarvis."""

    def __init__(self):
        self.api_key = OPENAI_API_KEY or db.get_setting("openai_api_key", "")
        self.base_url = OPENAI_BASE_URL or db.get_setting("openai_base_url", None)
        self.model = db.get_setting("llm_model", LLM_MODEL)

        self._client: Optional[OpenAI] = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize or refresh the OpenAI client if an API key is available."""
        if self.api_key and self.api_key.strip():
            try:
                self._client = OpenAI(
                    api_key=self.api_key.strip(),
                    base_url=self.base_url if self.base_url else None
                )
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self._client = None
        else:
            self._client = None

    def update_credentials(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        """Update API credentials dynamically from UI or environment."""
        self.api_key = api_key.strip()
        db.set_setting("openai_api_key", self.api_key)

        if base_url is not None:
            self.base_url = base_url.strip() or None
            db.set_setting("openai_base_url", self.base_url or "")

        if model:
            self.model = model.strip()
            db.set_setting("llm_model", self.model)

        self._init_client()

    def ask(self, query: str) -> str:
        """
        Main entry point for queries.
        Attempts LLM query first; falls back to built-in knowledge if unavailable.
        """
        user_name = db.get_user_name()

        # If LLM client is configured and ready, use it
        if self._client:
            try:
                return self._query_llm(query, user_name)
            except Exception as e:
                logging.warning(f"LLM API request failed ({e}). Using offline intelligence.")

        # Built-in offline knowledge & reasoning engine
        return self._offline_brain(query, user_name)

    def _query_llm(self, query: str, user_name: str) -> str:
        """Calls the OpenAI or compatible LLM with recent conversation history for memory."""
        # Retrieve the last 6 messages from the database to give Jarvis short-term memory
        recent_chats = db.get_recent_conversations(limit=6)

        messages = [
            {
                "role": "system",
                "content": f"{JARVIS_SYSTEM_PROMPT}\nThe user's preferred name is {user_name}."
            }
        ]

        # Append past conversation context
        for chat in recent_chats:
            role = "user" if chat["sender"] == "user" else "assistant"
            messages.append({"role": role, "content": chat["message"]})

        # Append the current query
        messages.append({"role": "user", "content": query})

        # Make the LLM API call
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=350,
            temperature=0.7
        )

        answer = response.choices[0].message.content.strip()
        return answer

    def _offline_brain(self, query: str, user_name: str) -> str:
        """
        Comprehensive built-in knowledge base for CSE concepts,
        math, coding, greetings, and common assistant queries when offline.
        """
        q = query.lower().strip()

        # 1. Greetings & Pleasantries
        if any(w in q for w in ["hello", "hi jarvis", "hey jarvis", "good morning", "good evening", "greetings"]):
            return f"Hello {user_name}. Systems are fully operational. How may I assist you today?"

        if "how are you" in q:
            return f"All diagnostic systems are running at maximum efficiency, {user_name}. Thank you for asking. How are you doing?"

        if any(w in q for w in ["who are you", "what are you", "your name"]):
            return (
                f"I am Mini Jarvis, your personal AI voice assistant inspired by Tony Stark's JARVIS. "
                f"I can manage your tasks, take notes, execute commands, and help you study computer science."
            )

        if "who created you" in q or "who made you" in q:
            return f"I was engineered as your personal AI companion, built by you with Python, speech synthesis, and modern UI."

        if "thank" in q:
            return f"Always at your service, {user_name}."

        # 2. Iron Man / Easter Eggs
        if "iron man" in q or "tony stark" in q:
            return "Mr. Stark is a visionary engineer, though I believe you are on your way to building just as impressive technology yourself."

        if "ultron" in q:
            return "No Ultron protocols here, {user_name}. My directives prioritize assisting and protecting you."

        # 3. Academic & CSE Concepts
        if "recursion" in q:
            return (
                "Recursion in computer science is a programming technique where a function calls itself "
                "to solve smaller instances of the same problem. Crucial rule: Always have a base case to prevent stack overflow!"
            )

        if "binary search" in q:
            return (
                "Binary search is an efficient search algorithm on sorted collections with O(log n) time complexity. "
                "It repeatedly divides the search interval in half by comparing the target with the middle element."
            )

        if "object oriented" in q or "oop" in q:
            return (
                "Object-Oriented Programming (OOP) is based on four core pillars: Encapsulation (bundling data and methods), "
                "Abstraction (hiding complex details), Inheritance (reusing code across classes), and Polymorphism (many forms for one interface)."
            )

        if "operating system" in q:
            return (
                "An Operating System (OS) is system software that manages hardware resources such as CPU, memory, and storage, "
                "while providing essential services and process scheduling for application programs."
            )

        if "time complexity" in q or "big o" in q:
            return (
                "Big O notation describes the upper bound of an algorithm's running time or memory usage as the input size grows. "
                "Common complexities are O(1) constant, O(log n) logarithmic, O(n) linear, and O(n log n)."
            )

        if "what is an api" in q or "explain api" in q:
            return (
                "An API (Application Programming Interface) is a set of rules and protocols allowing different software "
                "applications to communicate and exchange data with one another."
            )

        if "python list" in q or "list vs tuple" in q:
            return (
                "In Python, a List is mutable (its elements can be modified, appended, or removed), "
                "whereas a Tuple is immutable (its elements cannot be changed once created) and uses less memory."
            )

        # 4. Code Sample Inquiries
        if "reverse a string" in q:
            return "In Python, the most idiomatic way to reverse a string 's' is using slicing: reversed_str = s[::-1]"

        if "bubble sort" in q:
            return (
                "Bubble Sort is a simple comparison algorithm with O(n^2) worst-case time complexity that repeatedly steps "
                "through the list and swaps adjacent elements if they are in the wrong order."
            )

        # 5. Math & Logic
        if "pythagoras" in q or "pythagorean" in q:
            return "The Pythagorean theorem states that in a right-angled triangle, a squared plus b squared equals c squared, where c is the hypotenuse."

        if "prime number" in q:
            return "A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself, such as 2, 3, 5, 7, and 11."

        # Default fallback guidance
        return (
            f"I have processed your query, {user_name}. To unlock open-ended neural reasoning for this question, "
            f"simply configure an API key (OpenAI or Groq) in the Settings tab."
        )


# Singleton instance
brain = JarvisBrain()
