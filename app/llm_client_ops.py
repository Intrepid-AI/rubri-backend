import os
import logging
import yaml # Added for YAML loading
from typing import Dict, Any, Optional, List, AsyncIterator
from enum import Enum

# Default invoke parameters (can be customized per provider if needed)
default_invoke_params: Dict[str, Any] = {}

# LangChain imports
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.exceptions import LangChainException

# Provider-specific imports
from langchain_openai import ChatOpenAI, AzureChatOpenAI

# Optional Portkey support
try:
    from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
    PORTKEY_AVAILABLE = True
except ImportError:
    PORTKEY_AVAILABLE = False

logger = logging.getLogger(__name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(APP_DIR, 'configs', 'app.dev.yaml')

def load_and_validate_llm_config_from_yaml(file_path: str = CONFIG_FILE_PATH) -> Dict[str, Any]:
    """
    Loads LLM provider configurations from the app.dev.yaml file
     and validates its structure.
    """
    try:
        with open(file_path, 'r') as f:
            full_config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"LLM Config YAML not found: {file_path}")
        raise 
    except yaml.YAMLError as e:
        logger.error(f"Error parsing LLM Config YAML {file_path}: {e}")
        raise 

    if not isinstance(full_config, dict):
        raise ValueError(f"Invalid YAML format in {file_path}. Expected a dictionary.")

    llm_providers_config = full_config.get("llm_providers")
    if not isinstance(llm_providers_config, dict):
        raise ValueError(
            f"'llm_providers' key not found or not a dictionary in {file_path}."
        )

    for provider_name, p_config in llm_providers_config.items():
        if not isinstance(p_config, dict):
            raise ValueError(
                f"Configuration for provider '{provider_name}' under 'llm_providers' "
                f"must be a dictionary in {file_path}."
            )
        
        constructor_params = p_config.get("constructor_params")
        invoke_params = p_config.get("invoke_params")

        if not isinstance(constructor_params, dict):
            raise ValueError(
                f"'constructor_params' missing or not a dictionary for provider '{provider_name}' in {file_path}."
            )

        if invoke_params is not None and not isinstance(invoke_params, dict):
            raise ValueError(
                f"'invoke_params' must be a dictionary or omitted for provider '{provider_name}' in {file_path}."
            )

        if not invoke_params:
            invoke_params = default_invoke_params


        if provider_name == "openai":
            if "model" not in constructor_params:
                raise ValueError(f"'model' is missing in constructor_params for openai in {file_path}.")

        elif provider_name == "azure_openai":
            if "azure_deployment" not in constructor_params:
                raise ValueError(f"'azure_deployment' is missing in constructor_params for azure_openai in {file_path}.")

        elif provider_name == "gemini":
            if "model" not in constructor_params:
                raise ValueError(f"'model' is missing in constructor_params for gemini in {file_path}.")

        elif provider_name == "groq":
            if "model" not in constructor_params:
                raise ValueError(f"'model' is missing in constructor_params for groq in {file_path}.")

        elif provider_name == "portkey":
            if "model" not in constructor_params:
                raise ValueError(f"'model' is missing in constructor_params for portkey in {file_path}.")

    logger.info(f"Successfully loaded and validated LLM provider configurations from {file_path}")
    return llm_providers_config


class ModelProvider(str, Enum):
    """Enum for supported model providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    GEMINI = "gemini"
    GROQ = "groq"
    PORTKEY = "portkey"

class LLM_Client_Ops:
    """
    Operations manager for interacting with various LLM providers via LangChain.
    """
    _loaded_llm_yaml_config: Optional[Dict[str, Any]] = None
    
    # Providers that support streaming
    STREAMING_PROVIDERS = {
        ModelProvider.OPENAI,
        ModelProvider.AZURE_OPENAI,
        ModelProvider.GEMINI,
        ModelProvider.GROQ,
        # Portkey depends on underlying provider
    }

    @classmethod
    def _get_llm_yaml_config(cls) -> Dict[str, Any]:
        """Loads and caches the LLM configuration from the YAML file."""
        if cls._loaded_llm_yaml_config is None:
            cls._loaded_llm_yaml_config = load_and_validate_llm_config_from_yaml()
        return cls._loaded_llm_yaml_config


    def __init__(self, provider_name: str): 
        """
        Initialize the LLM operations manager with a specific provider.

        Args:
            provider_name: The name of the LLM provider (e.g., "openai", "gemini").
        """
        self.provider_name = provider_name.lower()
        
        all_llm_yaml_configs = LLM_Client_Ops._get_llm_yaml_config()

        self.provider_yaml_config = all_llm_yaml_configs.get(self.provider_name)

        if self.provider_yaml_config is None:
            raise ValueError(
                f"Configuration for provider '{self.provider_name}' not found in "
                f"{CONFIG_FILE_PATH} under 'llm_providers'."
            )

        self.llm_client: Optional[BaseChatModel] = None
        self._invoke_params: Dict[str, Any] = {} 
        self._supports_streaming = False
        
        self.validate_environment_and_config()
        self._initialize_client()
        self._check_streaming_support()

    def validate_environment_and_config(self):

        provider = ModelProvider(self.provider_name)

        if provider == ModelProvider.OPENAI:
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key env var OPENAI_API_KEY is required.")

        elif provider == ModelProvider.AZURE_OPENAI:
            if not os.environ.get("AZURE_OPENAI_API_KEY"):
                raise ValueError("Azure OpenAI API key env var AZURE_OPENAI_API_KEY is required.")

            if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
                raise ValueError("Azure OpenAI Endpoint env var AZURE_OPENAI_ENDPOINT is required.")

            if not os.environ.get("AZURE_API_VERSION"):
                raise ValueError("Azure OpenAI API Version env var AZURE_API_VERSION is required.")

            constructor_params = self.provider_yaml_config.get("constructor_params", {})
            if not constructor_params.get("azure_deployment"):
                raise ValueError("Azure OpenAI 'azure_deployment' is required in YAML config under 'constructor_params'.")

        elif provider == ModelProvider.GEMINI:
            if not os.environ.get("GOOGLE_API_KEY"):
                raise ValueError("Gemini API key env var GOOGLE_API_KEY is required.")

        elif provider == ModelProvider.GROQ:
            if not os.environ.get("GROQ_API_KEY"):
                raise ValueError("Groq API key env var GROQ_API_KEY is required.")

        elif provider == ModelProvider.PORTKEY:
            if not PORTKEY_AVAILABLE:
                raise ImportError("Portkey SDK not installed.")
            if not os.environ.get("PORTKEY_API_KEY"):
                raise ValueError("Portkey API key env var PORTKEY_API_KEY is required.")


    def _initialize_client(self):

        provider = ModelProvider(self.provider_name)

        constructor_params = self.provider_yaml_config.get("constructor_params", {})
        invoke_params = self.provider_yaml_config.get("invoke_params", {})

        if not invoke_params:
            invoke_params = default_invoke_params
        
        self._invoke_params = invoke_params

        try:
            if provider == ModelProvider.OPENAI:
                api_key = os.environ.get("OPENAI_API_KEY")
                self.llm_client = ChatOpenAI(api_key=api_key, **constructor_params)
            
            elif provider == ModelProvider.AZURE_OPENAI:
                api_key = os.environ.get("AZURE_OPENAI_API_KEY")
                openai_api_version = os.environ.get("AZURE_API_VERSION")
                openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

                self.llm_client = AzureChatOpenAI(api_key=api_key, 
                                                   openai_api_version=openai_api_version,
                                                   azure_endpoint=openai_endpoint,
                                                   **constructor_params)

            elif provider == ModelProvider.GEMINI:
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = os.environ.get("GOOGLE_API_KEY")
                self.llm_client = ChatGoogleGenerativeAI(google_api_key=api_key, **constructor_params)

            elif provider == ModelProvider.GROQ:
                from langchain_groq import ChatGroq
                api_key = os.environ.get("GROQ_API_KEY")
                self.llm_client = ChatGroq(api_key=api_key, **constructor_params)

            elif provider == ModelProvider.PORTKEY:
                portkey_api_key = os.environ.get("PORTKEY_API_KEY")

                portkey_routing_config = self._invoke_params.get("portkey_config")

                self.llm_client = ChatOpenAI(
                    api_key="X", # Placeholder for Portkey
                    base_url=PORTKEY_GATEWAY_URL,
                    default_headers=createHeaders(api_key=portkey_api_key, config=portkey_routing_config),
                    **constructor_params # Pass model, temperature etc. via Portkey
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider_name}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client for {self.provider_name}: {e}")
            self.llm_client = None
            raise
    
    def health_check(self) -> bool:

        if not self.llm_client:
            logger.error("Health check failed: LLM client not initialized.")
            return False

        try:

            messages = [HumanMessage(content="Hello")]

            response = self.llm_client.invoke(
                messages,
                config={"timeout": 5}, 
                **self._invoke_params 
            )

            if response and response.content:
                logger.info(f"Health check successful for {self.provider_name}.")
                return True
            else:
                logger.warning(f"Health check for {self.provider_name} returned empty response.")
                return False
            
        except Exception as e:
            logger.error(f"Health check failed for {self.provider_name}: {e}")
            return False

    def _check_streaming_support(self):
        """Check if the current provider supports streaming."""
        try:
            provider = ModelProvider(self.provider_name)
            self._supports_streaming = provider in self.STREAMING_PROVIDERS
            
            # For Portkey, check the underlying provider
            if provider == ModelProvider.PORTKEY:
                # For now, assume Portkey supports streaming
                # In production, you'd check the actual routing config
                self._supports_streaming = True
                
            logger.info(f"Provider {self.provider_name} streaming support: {self._supports_streaming}")
        except:
            self._supports_streaming = False
    
    @property
    def supports_streaming(self) -> bool:
        """Check if the provider supports streaming."""
        return self._supports_streaming

    def generate_text(self, prompt: str, system_message: Optional[str] = None) -> str:

        if not self.llm_client:
            raise RuntimeError("LLM client is not initialized.")

        messages: List[Any] = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        try:
            # Pass invoke_params to the invoke method
            response = self.llm_client.invoke(messages, **self._invoke_params)
            return response.content
        except Exception as e:
            logger.error(f"Text generation failed for {self.provider_name}: {e}")
            raise RuntimeError(f"Text generation failed: {e}")
    
    async def generate_text_stream(self, prompt: str, system_message: Optional[str] = None) -> AsyncIterator[str]:
        """
        Generate text with streaming support.
        
        Args:
            prompt: The user prompt
            system_message: Optional system message
            
        Yields:
            String chunks of the generated text
        """
        if not self.llm_client:
            raise RuntimeError("LLM client is not initialized.")
        
        if not self._supports_streaming:
            # Fallback for non-streaming providers
            result = self.generate_text(prompt, system_message)
            yield result
            return
        
        messages: List[BaseMessage] = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        try:
            # Use astream for streaming responses
            async for chunk in self.llm_client.astream(messages, **self._invoke_params):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Text streaming failed for {self.provider_name}: {e}")
            raise RuntimeError(f"Text streaming failed: {e}")
    
    def invoke_with_structured_output(self, messages: List[BaseMessage], 
                                    structured_output_model: type) -> Any:
        """
        Invoke the LLM with structured output support.
        
        Args:
            messages: List of messages to send
            structured_output_model: Pydantic model for structured output
            
        Returns:
            Instance of the structured output model
        """
        if not self.llm_client:
            raise RuntimeError("LLM client is not initialized.")
        
        try:
            # Create a new client with structured output
            structured_client = self.llm_client.with_structured_output(structured_output_model)
            response = structured_client.invoke(messages, **self._invoke_params)
            return response
        except Exception as e:
            logger.error(f"Structured output generation failed for {self.provider_name}: {e}")
            raise RuntimeError(f"Structured output generation failed: {e}")
    
    async def agenerate_text(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Async version of generate_text.
        
        Args:
            prompt: The user prompt
            system_message: Optional system message
            
        Returns:
            Generated text
        """
        if not self.llm_client:
            raise RuntimeError("LLM client is not initialized.")
        
        messages: List[BaseMessage] = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = await self.llm_client.ainvoke(messages, **self._invoke_params)
            return response.content
        except Exception as e:
            logger.error(f"Async text generation failed for {self.provider_name}: {e}")
            raise RuntimeError(f"Async text generation failed: {e}")


if __name__ == "__main__":
    # --- Add this section for dotenv ---
    from dotenv import load_dotenv
    import sys

    PROJECT_ROOT = os.path.dirname(APP_DIR) # APP_DIR is defined above as dirname of llm_ops.py
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded environment variables from: {dotenv_path}")
    else:
        print(f".env file not found at {dotenv_path}. "
              "Ensure it exists or environment variables are set externally.", file=sys.stderr)
    # --- End dotenv section ---

    # Example 1: OpenAI
    print("--- Testing OpenAI ---")
    try:
        # LLM_Client_Ops now only needs the provider name. It loads its own config from YAML.
        openai_ops = LLM_Client_Ops(provider_name="openai")
        print(f"OpenAI Health Check: {openai_ops.health_check()}")
        if openai_ops.health_check():
             print(f"OpenAI Generate Text: {openai_ops.generate_text('What is the capital of France?')}")
    except Exception as e:
        print(f"OpenAI Test Failed: {e}")

    # Example 2: Gemini
    print("\n--- Testing Gemini ---")
    try:
        gemini_ops = LLM_Client_Ops(provider_name="gemini")
        print(f"Gemini Health Check: {gemini_ops.health_check()}")
        if gemini_ops.health_check():
            print(f"Gemini Generate Text: {gemini_ops.generate_text('What is the capital of France?')}")
    except Exception as e:
        print(f"Gemini Test Failed: {e}")

    # Example 3: Groq
    print("\n--- Testing Groq ---")
    try:
        groq_ops = LLM_Client_Ops(provider_name="groq")
        print(f"Groq Health Check: {groq_ops.health_check()}")
        if groq_ops.health_check():
            print(f"Groq Generate Text: {groq_ops.generate_text('What is the capital of France?')}")
    except Exception as e:
        print(f"Groq Test Failed: {e}")

    # Example 4: Azure
    print("\n--- Testing Azure OpenAI ---")
    try:
        azure_ops = LLM_Client_Ops(provider_name="azure_openai")
        print(f"Azure OpenAI Health Check: {azure_ops.health_check()}")
        if azure_ops.health_check():
            print(f"Azure OpenAI Generate Text: {azure_ops.generate_text('What is the capital of France?')}")
    except Exception as e:
        print(f"Azure OpenAI Test Failed: {e}")
