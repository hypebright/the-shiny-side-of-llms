from chatlas import ChatAnthropic, interpolate_file
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field

chat = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    system_prompt="You are a presentation coach for data scientists. You give constructive, focused, and practical feedback on titles, structure, and storytelling.",
)

# Set model parameters (optional)
chat.set_model_params(
    temperature=0.8,  # default is 1
)

# chat.chat(
#     """I'm working on a presentation with the title: 'The Shiny Side of LLMs'.
#         Please evaluate the clarity, tone, and relevance of this title for the intended audience.
#         For context, this is a 10-minute lightning talk at posit::conf(2025).
#         The audience is Python and R users who are curious about AI and large language models,
#         but not all of them have a deep technical background.
#         The talk uses Shiny as a way to explore and demo LLMs in practice.
#         Return your answer as a JSON array of objects, where each object has the following keys:
#         - 'aspect': one of 'clarity', 'tone', or 'relevance'
#         - 'feedback': your concise assessment
#         - 'suggestion': an optional improvement if applicable"""
# )

# Get Quarto presentation and convert to plain Markdown
subprocess.run(["quarto", "render", "./Quarto/my-presentation.qmd", "--to", "markdown"])

# Use prompt file
prompt_file = "./prompts/prompt-analyse-slides-structured.md"

# Dynamic data
# Audience, length in minutes, type, and event
audience_content = "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content = "10"
type_content = "lightning talk"
event_content = "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file = Path("./Quarto/docs/my-presentation.md")
markdown_content = markdown_file.read_text(encoding="utf-8")

prompt_complete = interpolate_file(
    prompt_file,
    variables={
        "audience": audience_content,
        "length": length_content,
        "type": type_content,
        "event": event_content,
        "markdown": markdown_content,
    },
)


# Define data structure to extract from the input
class ScoreWithJustification(BaseModel):
    score: int = Field(..., ge=0, le=10, description="Score from 1 to 10.")
    justification: str = Field(
        ..., description="Brief explanation justifying the score."
    )


class SuggestedImprovements(BaseModel):
    pacing: str | None = Field(
        None,
        description="Suggestions for improving pacing and structure: e.g. slides where pacing might be too fast or too slow based on the content density. Suggestions include slides that can be combined or split.",
    )
    visual_design: str | None = Field(
        None,
        description="Suggestions for improving visual clarity or design: e.g. flag slides that are too text-heavy or cluttered. Includes recommendations for slide redesign like splitting text, adding visuals, or adding bullet points.",
    )
    storytelling: str | None = Field(
        None,
        description="Suggestions for improving storytelling or logical flow: e.g. if the presentation can be improved by adding a motivating opening, summarizing key points before transitions, and a clear closure.",
    )
    consistency: str | None = Field(
        None,
        description="Suggestions for improving consistency of style and structure: e.g. sudden shifts in slide formatting, tone, and visual elements that feel unintentional.",
    )
    engagement: str | None = Field(
        None,
        description="Suggestions to make the presentation more engaging: e.g. if the presentation can be improved by adding interactive elements like questions, polls and demos, while keeping the time constraint in mind.",
    )
    accessibility: str | None = Field(
        None,
        description="Suggestions for accessibility: e.g. slides with small text, poor color contrast, or a visual overload.",
    )


class DeckAnalysis(BaseModel):
    presentation_title: str = Field(..., description="The presentation title.")
    total_slides: int = Field(..., ge=0, description="Total number of slides.")
    percent_with_code: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of slides containing code blocks.",
    )
    percent_with_images: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of slides containing images."
    )
    estimated_duration_minutes: int = Field(
        ...,
        ge=0,
        description="Estimated presentation length in minutes, assuming ~1 minute per text slide and 2–3 minutes per code or image-heavy slide).",
    )
    clarity_score: ScoreWithJustification = Field(
        ..., description=" Clarity of content and concise explanation."
    )
    tone: str = Field(
        ...,
        description="Brief description of the presentation tone (e.g., informal, technical, playful).",
    )
    relevance_for_audience: ScoreWithJustification = Field(
        ..., description="Relevance for intended audience and concise explanation."
    )
    suggested_improvements: SuggestedImprovements = Field(
        ...,
        description="Improvement suggestions, or None per category if no improvements are needed.",
    )


chat.extract_data(prompt_complete, data_model=DeckAnalysis)

# Get tokens for this script
chat.get_tokens()
chat.get_cost(
    options="all",
    token_price=(0.003, 0.015),  # input: $3, output: $15 per million tokens
)
