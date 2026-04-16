"""
NLP text processing pipeline for grievances.
Includes: tokenization, lemmatization, cleaning, vectorization.
"""

import re
import logging
from typing import List, Dict, Tuple
import string

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from src.utils import get_logger

logger = get_logger(__name__)

# Download NLTK data (run once) - robust approach
def _ensure_nltk_data():
    """Ensure required NLTK data is available."""
    # Try to download punkt_tab (newer NLTK) or punkt (older NLTK)
    try:
        logger.debug("Downloading NLTK point data...")
        nltk.download('punkt_tab', quiet=True)
    except Exception as e:
        logger.debug(f"punkt_tab download failed, trying punkt: {e}")
        try:
            nltk.download('punkt', quiet=True)
        except Exception:
            logger.warning("Could not download punkt/punkt_tab, tokenization may fail")
    
    # Download other required data
    for data_name in ['stopwords', 'wordnet']:
        try:
            nltk.download(data_name, quiet=True)
        except Exception as e:
            logger.warning(f"Could not download NLTK {data_name}: {e}")

_ensure_nltk_data()


class TextProcessor:
    """Text preprocessing and vectorization."""
    
    def __init__(self, language: str = 'english'):
        """
        Initialize text processor.
        
        Args:
            language: Language for stopwords (default: English)
        """
        self.language = language
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words(language))
        self.vectorizer = None
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text
        
        Returns:
            Cleaned text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters and numbers (keep only letters and spaces)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Input text
        
        Returns:
            List of tokens
        """
        tokens = word_tokenize(text)
        return tokens
    
    def lemmatize(self, tokens: List[str]) -> List[str]:
        """
        Lemmatize tokens.
        
        Args:
            tokens: List of tokens
        
        Returns:
            List of lemmatized tokens
        """
        lemmatized = [self.lemmatizer.lemmatize(token) for token in tokens]
        return lemmatized
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """
        Remove stopwords.
        
        Args:
            tokens: List of tokens
        
        Returns:
            Filtered tokens (length > 2)
        """
        filtered = [
            token for token in tokens
            if token not in self.stop_words and len(token) > 2
        ]
        return filtered
    
    def process(self, text: str) -> List[str]:
        """
        Full processing pipeline: clean → tokenize → lemmatize → remove stopwords.
        
        Args:
            text: Raw text
        
        Returns:
            Processed tokens
        """
        text = self.clean_text(text)
        tokens = self.tokenize(text)
        tokens = self.lemmatize(tokens)
        tokens = self.remove_stopwords(tokens)
        return tokens
    
    def preprocess_batch(self, texts: List[str]) -> List[str]:
        """
        Preprocess multiple texts (cleaning only, for TF-IDF).
        
        Args:
            texts: List of raw texts
        
        Returns:
            List of cleaned texts
        """
        return [self.clean_text(text) for text in texts]
    
    def vectorize_tfidf(self, texts: List[str], max_features: int = 100) -> Tuple[np.ndarray, TfidfVectorizer]:
        """
        Vectorize texts using TF-IDF.
        
        Args:
            texts: List of texts
            max_features: Maximum number of features
        
        Returns:
            Tuple of (tfidf_matrix, vectorizer_object)
        """
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            min_df=2,  # Minimum document frequency
            max_df=0.8,  # Maximum document frequency
            lowercase=True,
            stop_words=self.language,
        )
        
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        logger.info(f"TF-IDF vectorization: {tfidf_matrix.shape[0]} documents, {tfidf_matrix.shape[1]} features")
        
        return tfidf_matrix, self.vectorizer
    
    def get_tfidf_feature_names(self) -> List[str]:
        """Get feature names from fitted TF-IDF vectorizer."""
        if self.vectorizer is None:
            return []
        return self.vectorizer.get_feature_names_out().tolist()
    
    def extract_keywords_from_cluster(self, texts: List[str], top_n: int = 5) -> List[str]:
        """
        Extract top keywords from a cluster of texts.
        
        Args:
            texts: List of texts in cluster
            top_n: Number of top keywords to return
        
        Returns:
            List of top keywords
        """
        # Process texts
        all_tokens = []
        for text in texts:
            tokens = self.process(text)
            all_tokens.extend(tokens)
        
        # Count frequency
        from collections import Counter
        token_counts = Counter(all_tokens)
        
        # Get top keywords
        top_keywords = [token for token, _ in token_counts.most_common(top_n)]
        
        return top_keywords


def get_text_processor(language: str = 'english') -> TextProcessor:
    """Factory function to get a text processor."""
    return TextProcessor(language=language)
