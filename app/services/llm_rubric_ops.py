import os
import json
import uuid
from typing import Dict, List, Tuple, Optional, Any
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.load import dumpd, load
from langchain_core.messages import messages_from_dict

from app.llm_client_ops import LLM_Client_Ops
from app.logger import get_logger
from app.constants import Constants
from app.db_ops import crud

logger = get_logger(__name__)

@lru_cache(maxsize=None)
def get_llm_instance() -> LLM_Client_Ops:
    try:
        llm_client = LLM_Client_Ops(provider_name="gemini")
        if llm_client.health_check():
            return llm_client
        else:
            logger.error("LLM health check failed")
            raise Exception("LLM health check failed")
    except Exception as e:
        logger.error(f"Error initializing LLM instance: {e}")
        raise

class PromptTemplateLoader:
    def __init__(self, prompt_templates_dir: str = Constants.PROMPTS_DIR.value):
        self.prompt_templates_dir = prompt_templates_dir
        if not os.path.exists(self.prompt_templates_dir):
            logger.error(f"Prompt templates directory not found: {self.prompt_templates_dir}")
            raise FileNotFoundError

    def load_template(self, scenario_path: str) -> str:
        filepath = os.path.join(self.prompt_templates_dir, scenario_path)
        try:
            with open(filepath, "r") as f:
                prompt_content = f.read()
                logger.debug(f"Loaded prompt template {scenario_path}: {filepath}")
                return prompt_content
            
        except FileNotFoundError:
            logger.error(f"Prompt template not found: {filepath}")
            raise

class RubricGenerator:
    def __init__(self, db):
        self.llm_client = get_llm_instance()
        self.prompt_loader = PromptTemplateLoader()
        self.db = db

    def generate_rubric(self, jd_text: str, resume_text: str = None) -> Dict[str, Any]:
        """
        Generate a rubric based on job description and optional resume.
        
        Args:
            jd: Job description text
            resume: Optional resume text
        
        Returns:
            Dictionary with response and conversation ID
        """
        # Create conversation chain with appropriate system message
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant for generating rubrics."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")  # This is key - use the {input} placeholder here
        ])

        memory = ConversationBufferMemory(return_messages=True, memory_key="history")
        conversation_chain = ConversationChain(
            llm=self.llm_client.llm_client,
            prompt=prompt,
            memory=memory,
            verbose=True
        )

        # Prepare the user message with the appropriate template
        if resume_text:
            prompt_template_path = "rubric_jd_res.md"
            prompt_content_tmp = self.prompt_loader.load_template(prompt_template_path)
            user_input = prompt_content_tmp.format(job_description=jd_text, resume=resume_text)
        else:
            prompt_template_path = "rubric_jd.md"
            prompt_content_tmp = self.prompt_loader.load_template(prompt_template_path)
            user_input = prompt_content_tmp.format(job_description=jd_text)

        # Generate response
        conversation_id = str(uuid.uuid4())
        response = conversation_chain.predict(input=user_input)  # Use user_input here

        # Save conversation history
        history_messages = conversation_chain.memory.chat_memory.messages
        serialized_messages = [dumpd(msg) for msg in history_messages]

        # Save to database
        rubric_record = crud.create_rubric(
            db=self.db,
            title=f"Rubric for JD {conversation_id}",
            description=f"Generated from job description",
            content={
                "response": response,
                "conversation_history": serialized_messages
            },
            status="draft"
        )

        return {
            "response": response,
            "conversation_id": conversation_id,
            "rubric_id": rubric_record.id
        }


    def rubric_modifications(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        """
        Continue the conversation for a given conversation ID and generate a new response.
        
        Args:
            conversation_id: ID of the existing conversation
            user_message: User's message to continue the conversation
        
        Returns:
            Dictionary with new response and updated conversation details
        """
        # Retrieve the existing rubric record
        rubric_record = crud.get_rubric(db=self.db, rubric_id=conversation_id)
        if not rubric_record:
            logger.error(f"Rubric not found for ID: {conversation_id}")
            raise ValueError(f"Rubric not found for ID: {conversation_id}")

        # Create conversation chain with the correct prompt structure
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant for generating rubrics."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")  # Use the {input} placeholder here
        ])

        memory = ConversationBufferMemory(return_messages=True, memory_key="history")
        
        # Restore previous messages to memory
        saved_history = rubric_record.content.get('conversation_history', [])
        if saved_history:
            loaded_messages = [load(msg_dict) for msg_dict in saved_history]
            memory.chat_memory.messages = loaded_messages

        conversation_chain = ConversationChain(
            llm=self.llm_client.llm_client,
            prompt=prompt,
            memory=memory,
            verbose=True
        )

        # Continue the conversation
        response = conversation_chain.predict(input=user_message)

        # Get updated conversation history
        history_messages = conversation_chain.memory.chat_memory.messages
        serialized_messages = [dumpd(msg) for msg in history_messages]

        # Update rubric in database
        updated_rubric = crud.update_rubric_via_chat(
            db=self.db,
            rubric_id=rubric_record.id,
            content={
                "response": response,
                "conversation_history": serialized_messages
            },
            message=user_message
        )

        return {
            "response": response,
            "conversation_id": conversation_id,
            "rubric_id": updated_rubric.id
        }

if __name__ == "__main__":
   
   from app.db_ops.database import SessionLocal
   db = SessionLocal()
   
   try:
       # Example Job Description
       jd_text = """
       We are looking for a highly skilled and experienced software engineer to join our team. The ideal candidate will have a strong background in Python and experience with various frameworks.  Responsibilities include designing, developing, and testing software applications.
       """
       
       # Example Resume (optional - can be None)
       resume_text = """
       John Doe
       Software Engineer
       10 years of experience in software development. Proficient in Python, Java, and C++.  Experience with various frameworks and technologies.
       """
       
       rubric_generator = RubricGenerator(db=db)
       
       # Generate rubric with resume
       result_with_resume = rubric_generator.generate_rubric(jd_text=jd_text, resume_text=resume_text)
       print("Rubric with Resume:", result_with_resume)
       
       # Generate rubric without resume
       result_without_resume = rubric_generator.generate_rubric(jd_text=jd_text)
       print("Rubric without Resume:", result_without_resume)
       
       # Example of rubric modifications
       conversation_id = result_with_resume["rubric_id"]  # Use rubric_id instead of conversation_id
       user_message = "Can you add more details about the experience required?"
       modified_rubric = rubric_generator.rubric_modifications(conversation_id=conversation_id, user_message=user_message)
       print("Modified Rubric:", modified_rubric)
       
   except Exception as e:
       print(f"An error occurred: {e}")
   finally:
       db.close()