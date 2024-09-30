from langfuse.decorators import observe
from typing import List, Optional
from generator import VertexAIGenerator
from dotenv import load_dotenv
import asyncio
load_dotenv()

# Define the prompt template
system_prompt = """
You are the steward of a group of chunks which represent groups of sentences that talk about a similar topic
A new proposition was just added to one of your chunks, you should generate a very brief 1-sentence summary which will inform viewers what a chunk group is about.

A good summary will say what the chunk is about, and give any clarifying instructions on what to add to the chunk.

You will be given a group of propositions which are in the chunk and the chunk's current summary.

Your summaries should anticipate generalization. If you get a proposition about apples, generalize it to food.
Or month, generalize it to "date and times".

Example:
Input: Proposition: Greg likes to eat pizza
Output: This chunk contains information about the types of food Greg likes to eat.

Only respond with the chunk's new summary, nothing else.

Chunk's propositions:
{proposition}

Current chunk summary:
{current_summary}

New summary:
"""

class ChunkSummaryUpdater:
    def __init__(
        self,
        generator: VertexAIGenerator
    ) -> None:
        self.generator = generator

    @observe(name="ChunkSummaryUpdater")
    async def run(
        self, proposition: str, current_summary: Optional[str] = None
    ) -> str:
        # If no current summary is provided, start with a default empty string
        if current_summary is None:
            current_summary = ""

        # Generate the updated summary using the generator
        updated_summary = await self.generator.run(
            prompt=system_prompt.format(proposition=proposition, current_summary=current_summary),
            temperature=0
            )
        return updated_summary.strip()

# Example usage
async def main():
    # Create an instance of the generator (e.g., VertexAIGenerator)
    generator = VertexAIGenerator()

    # Create an instance of ChunkSummaryUpdater
    chunk_updater = ChunkSummaryUpdater(generator=generator)

    # Example proposition and current summary
    proposition = "Greg likes to eat pizza"
    current_summary = ""

    # Update the summary
    updated_summary = await chunk_updater.run(proposition, current_summary)

    # Print the updated summary
    print(updated_summary)

asyncio.run(main())
