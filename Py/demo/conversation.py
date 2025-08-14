from dotenv import load_dotenv
from chatlas import ChatAnthropic, interpolate_file
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Optional, Union

load_dotenv()  # Loads key from the .env file

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

# Get Quarto presentation and convert to plain Markdown + HTML
subprocess.run(
    ["quarto", "render", "./Quarto/my-presentation.qmd", "--to", "markdown,html"]
)

# Use prompt file
# Step 1: first step of the analysis (meta-data)
prompt_file_1 = "./prompts/prompt-analyse-slides-structured-tool-1.md"
# Step 2: second step of the analysis (detailed analysis with improvements)
prompt_file_2 = Path("./prompts/prompt-analyse-slides-structured-tool-2.md")

# Dynamic data
# Audience, length in minutes, type, and event
audience_content = "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content = "10"
type_content = "lightning talk"
event_content = "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file = Path("./Quarto/docs/my-presentation.md")
markdown_content = markdown_file.read_text(encoding="utf-8")
html_file = Path("./Quarto/docs/my-presentation.html")

# Construct the first prompt
prompt_complete_1 = interpolate_file(
    prompt_file_1,
    variables={
        "audience": audience_content,
        "length": length_content,
        "type": type_content,
        "event": event_content,
        "html_file_path": html_file,
        "markdown": markdown_content,
    },
)

# Read the second prompt (no dynamic data)
prompt_complete_2 = prompt_file_2.read_text(encoding="utf-8")

# chat.chat(prompt_complete)


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
def calculate_slide_metric(html_file: str, metric: str) -> Union[int, float]:
    """
    Calculates the total number of slides, percentage of slides with code blocks,
    and percentage of slides with images in a Quarto presentation HTML file.

    Parameters
    ----------
    html_file : str
        Path to the HTML file generated by Quarto.
    metric : str
        The metric to calculate: "total_slides" for total number of slides,
        "code" for percentage of slides containing fenced code blocks,
        or "images" for percentage of slides containing images.

    Returns
    -------
    float or int
        The calculated metric value.
    """
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


chat.register_tool(calculate_slide_metric)

# Step 1: use regular chat to extract meta-data
# Note that this *should* make use of our tool
chat.chat(prompt_complete_1)

# Step 2: use structured chat to further analyse the slides
chat.extract_data(prompt_complete_2, data_model=DeckAnalysis)


# Get tokens for this script
chat.get_tokens()
chat.get_cost(
    options="all",
    token_price=(0.003, 0.015),  # input: $3, output: $15 per million tokens
)
