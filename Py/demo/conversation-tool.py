from dotenv import load_dotenv
from chatlas import ChatAnthropic, interpolate_file, interpolate
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Optional, Union

load_dotenv()  # Loads key from the .env file

# Get Quarto presentation and convert to plain Markdown + HTML
subprocess.run(
    ["quarto", "render", "./Quarto/my-presentation.qmd", "--to", "markdown,html"]
)

# Dynamic data
# Audience, length in minutes, type, and event
audience_content = "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content = "10"
type_content = "lightning talk"
event_content = "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file = Path("./Quarto/docs/my-presentation.md")
markdown_content = markdown_file.read_text(encoding="utf-8")

# Define prompt file
system_prompt_file = Path("./prompts/prompt-analyse-slides-structured-tool.md")

# Create system prompt
system_prompt = interpolate_file(
    system_prompt_file,
    variables={
        "audience": audience_content,
        "length": length_content,
        "type": type_content,
        "event": event_content,
        "markdown_content": markdown_content,
    },
)

# Define data structure to extract from the input
ScoreType = Annotated[int, Field(ge=0, le=10)]
PercentType = Annotated[float, Field(ge=0.0, le=100.0)]
MinutesType = Annotated[int, Field(ge=0)]
SlideCount = Annotated[int, Field(ge=0)]


class ScoringCategory(BaseModel):
    score: ScoreType = Field(..., description="Score from 1–10.")
    justification: str = Field(..., description="Brief explanation of the score.")
    improvements: Optional[str] = Field(
        None,
        description="Concise, actionable improvements, mentioning slide numbers if applicable.",
    )
    score_after_improvements: ScoreType = Field(
        ..., description="Estimated score after suggested improvements."
    )


class DeckAnalysis(BaseModel):
    presentation_title: str = Field(..., description="The presentation title.")
    total_slides: SlideCount
    percent_with_code: PercentType
    percent_with_images: PercentType
    estimated_duration_minutes: MinutesType
    tone: str = Field(
        ..., description="Brief description of the tone of the presentation."
    )

    clarity: ScoringCategory = Field(
        ...,
        description="Evaluate how clearly the ideas are communicated. Are the explanations easy to understand? Are terms defined when needed? Is the key message clear?",
    )
    relevance: ScoringCategory = Field(
        ...,
        description="Assess how well the content matches the audience’s background, needs, and expectations. Are examples, depth of detail, and terminology appropriate for the audience type?",
    )
    visual_design: ScoringCategory = Field(
        ...,
        description="Judge the visual effectiveness of the slides. Are they readable, visually balanced, and not overcrowded with text or visuals? Is layout used consistently?",
    )
    engagement: ScoringCategory = Field(
        ...,
        description="Estimate how likely the presentation is to keep attention. Are there moments of interactivity, storytelling, humor, or visual interest that invite focus?",
    )
    pacing: ScoringCategory = Field(
        ...,
        description="Analyze the distribution of content across slides. Are some slides too dense or too light? ",
    )
    structure: ScoringCategory = Field(
        ...,
        description="Review the logical flow of the presentation. Is there a clear beginning, middle, and end? Are transitions between topics smooth? Does the presentation build toward a conclusion?",
    )
    concistency: ScoringCategory = Field(  # spelling kept as-is
        ...,
        description="Evaluatue whether the presentation is consistent when it comes to formatting, tone, and visual elements. Are there any elements that feel out of place?",
    )
    accessibility: ScoringCategory = Field(
        ...,
        description="Consider how accessible the presentation would be for all viewers, including those with visual or cognitive challenges. Are font sizes readable? Is there sufficient contrast? Are visual elements not overwhelming?",
    )


# Define a tool to calculate some metrics
# Start with a function:
def calculate_slide_metric(metric: str) -> Union[int, float]:
    """
    Calculates the total number of slides, percentage of slides with code blocks,
    and percentage of slides with images in a Quarto presentation HTML file.

    Parameters
    ----------
    metric : str
        The metric to calculate: "total_slides" for total number of slides,
        "code" for percentage of slides containing fenced code blocks,
        or "images" for percentage of slides containing images.

    Returns
    -------
    float or int
        The calculated metric value.
    """
    html_file = Path("./Quarto/docs/my-presentation.html")
    if not html_file.exists():
        raise FileNotFoundError(f"HTML file {html_file} does not exist.")

    # Read HTML file
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Split on <section> tags to get individual slides
    slides = html_content.split("<section")
    total_slides = len(slides)

    if metric == "total_slides":
        result = total_slides
    elif metric == "code":
        slides_with_code = sum('class="sourceCode"' in slide for slide in slides)
        result = round((slides_with_code / total_slides) * 100, 2)
    elif metric == "images":
        slides_with_image = sum("<img" in slide for slide in slides)
        result = round((slides_with_image / total_slides) * 100, 2)
    else:
        raise ValueError("Unknown metric: choose 'total_slides', 'code', or 'images'")

    return result


# Initialise chat with Claude Sonnet 4 model
chat = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    system_prompt=system_prompt,
)

# Set model parameters (optional)
chat.set_model_params(
    temperature=0.8,  # default is 1
)

# Register the tool with the chat
chat.register_tool(calculate_slide_metric)

# Start conversation with the chat
# Task 1: regular chat to extract meta-data
chat.chat(
    interpolate(
        "Execute Task 1 (counts). Here are the slides in Markdown: {{ markdown_content }}"
    )
)

# Task 2: structured chat to further analyse the slides
chat.extract_data(
    "Execute Task 2 (suggestions)",
    data_model=DeckAnalysis,
)

# Get tokens for this script
chat.get_tokens()
chat.get_cost()
