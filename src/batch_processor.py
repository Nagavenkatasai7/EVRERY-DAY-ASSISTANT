"""
Batch API Processor
Handles asynchronous batch processing with Claude API for 50% cost savings
"""

import time
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, DATA_DIR
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError

logger = get_logger(__name__)

# Batch storage directory
BATCH_DIR = DATA_DIR / "batches"
BATCH_DIR.mkdir(parents=True, exist_ok=True)


class BatchProcessor:
    """
    Handles batch processing of Claude API requests for 50% cost savings

    Batch API is perfect for:
    - PDF processing and summary generation (non-time-critical)
    - Large-scale document analysis
    - Bulk Q&A generation
    - Any task that can wait up to 24 hours

    Note: Batch API offers 50% discount on both input and output tokens!
    """

    def __init__(self):
        """Initialize batch processor"""
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = CLAUDE_MODEL
        logger.info("Batch processor initialized")

    def create_batch(
        self,
        requests: List[Dict],
        batch_description: str = "Batch processing job"
    ) -> str:
        """
        Create a batch job with multiple requests

        Args:
            requests: List of request dictionaries with format:
                {
                    "custom_id": "unique_id",
                    "params": {
                        "model": "model_name",
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": "..."}],
                        "system": "system prompt" or [{"type": "text", "text": "..."}]
                    }
                }
            batch_description: Description of the batch job

        Returns:
            Batch ID for tracking

        Example:
            requests = [{
                "custom_id": "pdf_summary_1",
                "params": {
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": "Summarize this PDF..."}],
                    "system": [{"type": "text", "text": "You are an expert...", "cache_control": {"type": "ephemeral"}}]
                }
            }]
            batch_id = processor.create_batch(requests, "PDF batch summary")
        """
        try:
            logger.info(f"Creating batch job with {len(requests)} requests: {batch_description}")

            # Save requests to JSONL file (required format for batch API)
            batch_file_path = BATCH_DIR / f"batch_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

            with open(batch_file_path, 'w') as f:
                for request in requests:
                    f.write(json.dumps(request) + '\n')

            logger.info(f"Saved batch requests to {batch_file_path}")

            # Create the batch job via API
            batch = self.client.messages.batches.create(
                requests=requests
            )

            batch_id = batch.id
            logger.info(f"✅ Batch job created: {batch_id}")
            logger.info(f"💰 Expected savings: 50% on {len(requests)} requests")

            # Save batch metadata
            metadata = {
                "batch_id": batch_id,
                "description": batch_description,
                "num_requests": len(requests),
                "created_at": datetime.now().isoformat(),
                "status": "in_progress",
                "requests_file": str(batch_file_path)
            }

            metadata_path = BATCH_DIR / f"batch_metadata_{batch_id}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            return batch_id

        except Exception as e:
            logger.error(f"Failed to create batch: {str(e)}")
            raise ClaudeAPIError(f"Batch creation failed: {str(e)}")

    def get_batch_status(self, batch_id: str) -> Dict:
        """
        Get the status of a batch job

        Args:
            batch_id: Batch ID from create_batch

        Returns:
            Dictionary with status information:
            {
                "status": "in_progress" | "ended",
                "processing_status": "in_progress" | "ended",
                "request_counts": {
                    "processing": 0,
                    "succeeded": 10,
                    "errored": 0,
                    "canceled": 0,
                    "expired": 0
                },
                "created_at": "timestamp",
                "ended_at": "timestamp" (if complete)
            }
        """
        try:
            batch = self.client.messages.batches.retrieve(batch_id)

            status = {
                "status": batch.processing_status,
                "request_counts": {
                    "processing": batch.request_counts.processing,
                    "succeeded": batch.request_counts.succeeded,
                    "errored": batch.request_counts.errored,
                    "canceled": batch.request_counts.canceled,
                    "expired": batch.request_counts.expired
                },
                "created_at": batch.created_at,
                "ended_at": getattr(batch, 'ended_at', None)
            }

            logger.info(f"Batch {batch_id} status: {status['status']}")
            logger.info(f"  Succeeded: {status['request_counts']['succeeded']}, "
                       f"Processing: {status['request_counts']['processing']}, "
                       f"Errored: {status['request_counts']['errored']}")

            return status

        except Exception as e:
            logger.error(f"Failed to get batch status: {str(e)}")
            raise ClaudeAPIError(f"Status check failed: {str(e)}")

    def get_batch_results(self, batch_id: str, save_to_file: bool = True) -> List[Dict]:
        """
        Get results from a completed batch job

        Args:
            batch_id: Batch ID from create_batch
            save_to_file: Whether to save results to a JSON file (default: True)

        Returns:
            List of result dictionaries:
            [{
                "custom_id": "unique_id",
                "result": {
                    "type": "succeeded" | "errored",
                    "message": {...} (if succeeded),
                    "error": {...} (if errored)
                }
            }]
        """
        try:
            logger.info(f"Fetching results for batch {batch_id}...")

            # Check if batch is complete
            status = self.get_batch_status(batch_id)

            if status["status"] != "ended":
                logger.warning(f"Batch {batch_id} not yet complete (status: {status['status']})")
                return []

            # Get results
            results = []
            for result in self.client.messages.batches.results(batch_id):
                results.append(result.model_dump())

            logger.info(f"Retrieved {len(results)} results from batch {batch_id}")

            # Save to file if requested
            if save_to_file:
                results_file = BATCH_DIR / f"batch_results_{batch_id}.json"
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Saved results to {results_file}")

            return results

        except Exception as e:
            logger.error(f"Failed to get batch results: {str(e)}")
            raise ClaudeAPIError(f"Results retrieval failed: {str(e)}")

    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a batch job

        Args:
            batch_id: Batch ID to cancel

        Returns:
            True if successfully canceled
        """
        try:
            logger.info(f"Canceling batch {batch_id}...")
            batch = self.client.messages.batches.cancel(batch_id)
            logger.info(f"Batch {batch_id} canceled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel batch: {str(e)}")
            return False

    def wait_for_completion(
        self,
        batch_id: str,
        check_interval: int = 60,
        max_wait_hours: int = 24
    ) -> Dict:
        """
        Wait for batch to complete (polling)

        Args:
            batch_id: Batch ID to wait for
            check_interval: Seconds between status checks (default: 60)
            max_wait_hours: Maximum hours to wait (default: 24)

        Returns:
            Final status dictionary

        Note: This is a blocking operation. For production, consider using
        webhooks or checking status asynchronously.
        """
        max_checks = (max_wait_hours * 3600) // check_interval
        checks = 0

        logger.info(f"Waiting for batch {batch_id} to complete (checking every {check_interval}s)...")

        while checks < max_checks:
            status = self.get_batch_status(batch_id)

            if status["status"] == "ended":
                logger.info(f"✅ Batch {batch_id} completed!")
                return status

            checks += 1
            logger.info(f"Batch still processing... (check {checks}/{max_checks})")
            time.sleep(check_interval)

        logger.warning(f"Batch {batch_id} did not complete within {max_wait_hours} hours")
        return self.get_batch_status(batch_id)


def create_batch_request_for_summary(
    system_prompt: str,
    user_prompt: str,
    custom_id: str,
    max_tokens: int = 4096,
    use_cache: bool = True
) -> Dict:
    """
    Helper function to create a batch request for summary generation

    Args:
        system_prompt: System prompt text
        user_prompt: User prompt text
        custom_id: Unique identifier for this request
        max_tokens: Maximum tokens for response
        use_cache: Whether to use prompt caching (recommended for cost savings)

    Returns:
        Batch request dictionary ready for create_batch()

    Example:
        request = create_batch_request_for_summary(
            system_prompt="You are an expert...",
            user_prompt="Summarize this document...",
            custom_id="doc_summary_1",
            use_cache=True
        )
        batch_processor.create_batch([request], "Document summaries")
    """
    # Build system message with caching if enabled
    if use_cache:
        system_message = [{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        }]
    else:
        system_message = system_prompt

    return {
        "custom_id": custom_id,
        "params": {
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "system": system_message
        }
    }
