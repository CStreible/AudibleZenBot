"""
Blocked Terms Manager - Manage blocked words and phrases
"""

import json
from pathlib import Path
from typing import List, Set
from core.logger import get_logger

logger = get_logger(__name__)


class BlockedTermsManager:
    """Manages blocked terms/phrases for chat moderation"""
    
    def __init__(self):
        """Initialize blocked terms manager"""
        self.config_dir = Path.home() / ".audiblezenbot"
        self.config_dir.mkdir(exist_ok=True)
        self.blocked_terms_file = self.config_dir / "blocked_terms.json"
        self.blocked_terms: Set[str] = set()
        self.load()
    
    def load(self):
        """Load blocked terms from file"""
        if self.blocked_terms_file.exists():
            try:
                with open(self.blocked_terms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blocked_terms = set(data.get('blocked_terms', []))
                logger.info(f"Loaded {len(self.blocked_terms)} blocked terms")
            except Exception as e:
                logger.exception(f"Error loading blocked terms: {e}")
                self.blocked_terms = set()
        else:
            self.blocked_terms = set()
    
    def save(self):
        """Save blocked terms to file"""
        try:
            data = {
                'blocked_terms': sorted(list(self.blocked_terms))
            }
            with open(self.blocked_terms_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Saved {len(self.blocked_terms)} blocked terms")
        except Exception as e:
            logger.exception(f"Error saving blocked terms: {e}")
    
    def add_term(self, term: str):
        """Add a term to the blocked list"""
        term = term.strip().lower()
        if term:
            self.blocked_terms.add(term)
            self.save()
            logger.info(f"Added blocked term: {term}")
    
    def remove_term(self, term: str):
        """Remove a term from the blocked list"""
        term = term.strip().lower()
        if term in self.blocked_terms:
            self.blocked_terms.discard(term)
            self.save()
            logger.info(f"Removed blocked term: {term}")
    
    def is_blocked(self, message: str) -> bool:
        """Check if a message contains any blocked terms"""
        message_lower = message.lower()
        for term in self.blocked_terms:
            if term in message_lower:
                return True
        return False
    
    def get_blocked_terms_in_message(self, message: str) -> List[str]:
        """Get list of blocked terms found in a message"""
        message_lower = message.lower()
        found_terms = []
        for term in self.blocked_terms:
            if term in message_lower:
                found_terms.append(term)
        return found_terms
    
    def get_blocked_terms(self) -> List[str]:
        """Get list of all blocked terms"""
        return sorted(list(self.blocked_terms))
    
    def clear(self):
        """Clear all blocked terms"""
        self.blocked_terms.clear()
        self.save()
        logger.info("Cleared all blocked terms")


# Global instance
_blocked_terms_manager = None

def get_blocked_terms_manager() -> BlockedTermsManager:
    """Get the global blocked terms manager instance"""
    global _blocked_terms_manager
    if _blocked_terms_manager is None:
        _blocked_terms_manager = BlockedTermsManager()
    return _blocked_terms_manager
