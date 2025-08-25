from shiny import App, reactive, render, ui, req
import shinyswatch
import pandas as pd
import plotnine as p9
from dotenv import load_dotenv
from chatlas import ChatAnthropic, interpolate_file, interpolate
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Optional, Union
import tempfile
import shutil

load_dotenv()  # Loads key from the .env file

# Path to the current file
APP_DIR = Path(__file__).parent
# Root directory of the project
ROOT_DIR = APP_DIR.parent.parent


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


def make_frames(d: dict):
    # meta info (top-level keys that are not eval categories)
    meta_keys = [
        "presentation_title",
        "total_slides",
        "percent_with_code",
        "percent_with_images",
        "estimated_duration_minutes",
        "tone",
    ]
    meta = {k: d[k] for k in meta_keys}

    # eval categories (everything else)
    evals = []
    for k, v in d.items():
        if k not in meta_keys:
            # fix typo
            category = "consistency" if k == "concistency" else k
            evals.append(
                {
                    "category": category,
                    "score": v["score"],
                    "justification": v["justification"],
                    "improvements": v["improvements"],
                    "score_after_improvements": v["score_after_improvements"],
                }
            )

    evals_df = pd.DataFrame(evals)

    return {"meta": meta, "evals": evals_df}


# Icons
file_slides = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" class="bi bi-file-slides-fill" viewBox="0 0 16 16">
  <path d="M7 7.78V5.22c0-.096.106-.156.19-.106l2.13 1.279a.125.125 0 0 1 0 .214l-2.13 1.28A.125.125 0 0 1 7 7.778z"/>
  <path d="M12 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2M5 4h6a.5.5 0 0 1 .496.438l.5 4A.5.5 0 0 1 11.5 9h-3v2.016c.863.055 1.5.251 1.5.484 0 .276-.895.5-2 .5s-2-.224-2-.5c0-.233.637-.429 1.5-.484V9h-3a.5.5 0 0 1-.496-.562l.5-4A.5.5 0 0 1 5 4"/>
</svg>"""

file_code = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" class="bi bi-file-code-fill" viewBox="0 0 16 16">
  <path d="M12 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2M6.646 5.646a.5.5 0 1 1 .708.708L5.707 8l1.647 1.646a.5.5 0 0 1-.708.708l-2-2a.5.5 0 0 1 0-.708zm2.708 0 2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 1 1 .708-.708"/>
</svg>"""

file_image = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" class="bi bi-file-image-fill" viewBox="0 0 16 16">
  <path d="M4 0h8a2 2 0 0 1 2 2v8.293l-2.73-2.73a1 1 0 0 0-1.52.127l-1.889 2.644-1.769-1.062a1 1 0 0 0-1.222.15L2 12.292V2a2 2 0 0 1 2-2m4.002 5.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0"/>
  <path d="M10.564 8.27 14 11.708V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-.293l3.578-3.577 2.56 1.536 2.426-3.395z"/>
</svg>"""

robot = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-robot" viewBox="0 0 16 16">
  <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135"/>
  <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5"/>
</svg>"""

thumbs_up = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-hand-thumbs-up" viewBox="0 0 16 16">
  <path d="M8.864.046C7.908-.193 7.02.53 6.956 1.466c-.072 1.051-.23 2.016-.428 2.59-.125.36-.479 1.013-1.04 1.639-.557.623-1.282 1.178-2.131 1.41C2.685 7.288 2 7.87 2 8.72v4.001c0 .845.682 1.464 1.448 1.545 1.07.114 1.564.415 2.068.723l.048.03c.272.165.578.348.97.484.397.136.861.217 1.466.217h3.5c.937 0 1.599-.477 1.934-1.064a1.86 1.86 0 0 0 .254-.912c0-.152-.023-.312-.077-.464.201-.263.38-.578.488-.901.11-.33.172-.762.004-1.149.069-.13.12-.269.159-.403.077-.27.113-.568.113-.857 0-.288-.036-.585-.113-.856a2 2 0 0 0-.138-.362 1.9 1.9 0 0 0 .234-1.734c-.206-.592-.682-1.1-1.2-1.272-.847-.282-1.803-.276-2.516-.211a10 10 0 0 0-.443.05 9.4 9.4 0 0 0-.062-4.509A1.38 1.38 0 0 0 9.125.111zM11.5 14.721H8c-.51 0-.863-.069-1.14-.164-.281-.097-.506-.228-.776-.393l-.04-.024c-.555-.339-1.198-.731-2.49-.868-.333-.036-.554-.29-.554-.55V8.72c0-.254.226-.543.62-.65 1.095-.3 1.977-.996 2.614-1.708.635-.71 1.064-1.475 1.238-1.978.243-.7.407-1.768.482-2.85.025-.362.36-.594.667-.518l.262.066c.16.04.258.143.288.255a8.34 8.34 0 0 1-.145 4.725.5.5 0 0 0 .595.644l.003-.001.014-.003.058-.014a9 9 0 0 1 1.036-.157c.663-.06 1.457-.054 2.11.164.175.058.45.3.57.65.107.308.087.67-.266 1.022l-.353.353.353.354c.043.043.105.141.154.315.048.167.075.37.075.581 0 .212-.027.414-.075.582-.05.174-.111.272-.154.315l-.353.353.353.354c.047.047.109.177.005.488a2.2 2.2 0 0 1-.505.805l-.353.353.353.354c.006.005.041.05.041.17a.9.9 0 0 1-.121.416c-.165.288-.503.56-1.066.56z"/>
</svg>"""

thumbs_down = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-hand-thumbs-down" viewBox="0 0 16 16">
  <path d="M8.864 15.674c-.956.24-1.843-.484-1.908-1.42-.072-1.05-.23-2.015-.428-2.59-.125-.36-.479-1.012-1.04-1.638-.557-.624-1.282-1.179-2.131-1.41C2.685 8.432 2 7.85 2 7V3c0-.845.682-1.464 1.448-1.546 1.07-.113 1.564-.415 2.068-.723l.048-.029c.272-.166.578-.349.97-.484C6.931.08 7.395 0 8 0h3.5c.937 0 1.599.478 1.934 1.064.164.287.254.607.254.913 0 .152-.023.312-.077.464.201.262.38.577.488.9.11.33.172.762.004 1.15.069.13.12.268.159.403.077.27.113.567.113.856s-.036.586-.113.856c-.035.12-.08.244-.138.363.394.571.418 1.2.234 1.733-.206.592-.682 1.1-1.2 1.272-.847.283-1.803.276-2.516.211a10 10 0 0 1-.443-.05 9.36 9.36 0 0 1-.062 4.51c-.138.508-.55.848-1.012.964zM11.5 1H8c-.51 0-.863.068-1.14.163-.281.097-.506.229-.776.393l-.04.025c-.555.338-1.198.73-2.49.868-.333.035-.554.29-.554.55V7c0 .255.226.543.62.65 1.095.3 1.977.997 2.614 1.709.635.71 1.064 1.475 1.238 1.977.243.7.407 1.768.482 2.85.025.362.36.595.667.518l.262-.065c.16-.04.258-.144.288-.255a8.34 8.34 0 0 0-.145-4.726.5.5 0 0 1 .595-.643h.003l.014.004.058.013a9 9 0 0 0 1.036.157c.663.06 1.457.054 2.11-.163.175-.059.45-.301.57-.651.107-.308.087-.67-.266-1.021L12.793 7l.353-.354c.043-.042.105-.14.154-.315.048-.167.075-.37.075-.581s-.027-.414-.075-.581c-.05-.174-.111-.273-.154-.315l-.353-.354.353-.354c.047-.047.109-.176.005-.488a2.2 2.2 0 0 0-.505-.804l-.353-.354.353-.354c.006-.005.041-.05.041-.17a.9.9 0 0 0-.121-.415C12.4 1.272 12.063 1 11.5 1"/>
</svg>"""

sad_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-emoji-frown-fill text-warning" viewBox="0 0 16 16">
  <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16M7 6.5C7 7.328 6.552 8 6 8s-1-.672-1-1.5S5.448 5 6 5s1 .672 1 1.5m-2.715 5.933a.5.5 0 0 1-.183-.683A4.5 4.5 0 0 1 8 9.5a4.5 4.5 0 0 1 3.898 2.25.5.5 0 0 1-.866.5A3.5 3.5 0 0 0 8 10.5a3.5 3.5 0 0 0-3.032 1.75.5.5 0 0 1-.683.183M10 8c-.552 0-1-.672-1-1.5S9.448 5 10 5s1 .672 1 1.5S10.552 8 10 8"/>
</svg>"""

app_ui = ui.page_fillable(
    ## General theme and styles
    ## 1. Custom CSS
    ui.tags.style("""
        #suggested_improvements table {
            font-family: 'Lato', sans-serif;
            font-size: 11px;
        }
    """),
    ui.layout_sidebar(
        ui.sidebar(
            ui.div(
                ui.p(ui.strong("Hey, I am DeckCheck!")),
                ui.p(
                    """I can help you improve your Quarto presentations by analysing them and suggesting improvements. Before I can do that, I need some information about your presentation."""
                ),
            ),
            ui.input_file(
                "file",
                "Upload your Quarto presentation",
                accept=[".qmd", ".qmdx"],
                multiple=False,
            ),
            ui.input_text_area(
                "audience",
                "Describe your audience",
                height="150px",
                placeholder="e.g. Python and R users who are curious about AI and large language models, but not all of them have a deep technical background",
            ),
            ui.input_numeric(
                "length", "Time cap for the presentation (minutes)", value=10, min=1
            ),
            ui.input_text(
                "type",
                "Type of talk",
                placeholder="e.g. lightning talk, workshop, or keynote",
            ),
            ui.input_text("event", "Event name", placeholder="e.g. posit::conf(2025)"),
            ui.input_action_button(
                "submit",
                icon=ui.HTML(robot),
                label="Analyse presentation",
            ),
            width=400,
        ),
        ui.layout_column_wrap(
            ui.value_box(
                "Showtime",
                ui.output_text("showtime"),
                showcase=ui.HTML(file_slides),
                theme="primary",
            ),
            ui.value_box(
                "Code Savviness",
                ui.output_text("code_savviness"),
                showcase=ui.HTML(file_code),
                theme="primary",
            ),
            ui.value_box(
                "Image Presence",
                ui.output_text("image_presence"),
                showcase=ui.HTML(file_image),
                theme="primary",
            ),
            width=1 / 3,
            fill=False,
        ),
        ui.layout_column_wrap(
            ui.card(
                ui.card_header(ui.strong("Scores per category")),
                ui.output_plot("scores"),
                height="600px",
            ),
            ui.card(
                ui.card_header(ui.strong("Suggested improvements per category")),
                ui.output_table("suggested_improvements"),
                height="600px",
            ),
            width=1 / 2,
            fill=False,
        ),
        ui.div(
            ui.input_action_button(
                "like",
                icon=ui.HTML(thumbs_up),
                label="Like",
                class_="btn-success btn-sm",
                style="opacity: 0.75; margin-right: 10px;",
            ),
            ui.input_action_button(
                "dislike",
                icon=ui.HTML(thumbs_down),
                label="Dislike",
                class_="btn-danger btn-sm",
                style="opacity: 0.75;",
            ),
            class_="d-flex p-2 gap-2",
        ),
    ),
    theme=shinyswatch.theme.flatly,
)


def server(input, output, session):
    @reactive.calc
    @reactive.event(input.submit)
    async def analysis_result():
        try:
            if input.file() is not None:
                # Error for testing
                # raise ValueError("This is a test error")

                # Get file path of the uploaded file
                file_path = input.file()[0]["datapath"]

                # Copy the uploaded file to a temporary location with a fixed name
                temp_dir = tempfile.gettempdir()
                qmd_file = Path(temp_dir) / "my-presentation.qmd"

                shutil.copy(file_path, qmd_file)

                # Get Quarto presentation and convert to plain Markdown + HTML
                subprocess.run(
                    ["quarto", "render", str(qmd_file), "--to", "markdown,html"]
                )

                # Read the generated Markdown file containing our slides
                markdown_file = Path(temp_dir) / "my-presentation.md"
                markdown_content = markdown_file.read_text(encoding="utf-8")

                system_prompt_file = (
                    ROOT_DIR / "prompts" / "prompt-analyse-slides-structured-tool.md"
                )

                # Create system prompt
                system_prompt = interpolate_file(
                    system_prompt_file,
                    variables={
                        "audience": input.audience(),
                        "length": input.length(),
                        "type": input.type(),
                        "event": input.event(),
                        "markdown_content": markdown_content,
                    },
                )

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
                chat_res1 = await chat.chat_async(
                    interpolate(
                        "Execute Task 1 (counts). Here are the slides in Markdown: {{ markdown_content }}"
                    )
                )

                print(chat_res1)

                # Task 2: structured chat to further analyse the slides
                chat_res2 = await chat.extract_data_async(
                    "Execute Task 2 (suggestions)",
                    data_model=DeckAnalysis,
                )

                return make_frames(chat_res2)

        except Exception as e:
            # Log the error or return a user-friendly message
            print(f"Error during analysis: {e}")
            # Return value that triggers modal in UI
            m = ui.modal(
                ui.div(
                    # Sad bootstrap icon
                    ui.HTML(sad_icon),
                    ui.br(),
                    ui.p(
                        "The not so Shiny Side of LLMs. Please check that your Quarto presentation is valid and contains slides."
                    ),
                    # add class to center the content
                    class_="text-center",
                ),
                title="Oops, something went wrong!",
                easy_close=True,
                footer=ui.modal_button("Close"),
            )
            ui.modal_show(m)

            return None

    @render.plot
    async def scores():
        res = await analysis_result()

        req(res is not None)

        evals = res["evals"].copy()
        evals = evals.sort_values("score")
        evals["category"] = pd.Categorical(
            evals["category"], categories=evals["category"], ordered=True
        )

        # Create the plot using plotnine
        plot = (
            p9.ggplot(evals, p9.aes(x="category", y="score"))
            + p9.geom_col(fill="#18bc9c")
            + p9.labs(x="Category", y="Score")
            + p9.coord_flip()
            + p9.theme_minimal()
            + p9.theme(figure_size=(10, 8))
        )

        return plot

    @render.table
    async def suggested_improvements():
        res = await analysis_result()

        req(res is not None)

        evals = res["evals"].copy()
        evals["Gain"] = evals["score_after_improvements"] - evals["score"]

        result_table = evals.assign(
            Category=evals["category"].str.title(),
            **{"Current score": evals["score"]},
            Improvements=evals["improvements"],
            **{"Score After Improvements": evals["score_after_improvements"]},
            Gain=evals["Gain"],
        )[
            [
                "Category",
                "Current score",
                "Improvements",
                "Score After Improvements",
                "Gain",
            ]
        ].sort_values("Gain", ascending=False)

        return result_table

    @render.text
    async def showtime():
        res = await analysis_result()
        req(res is not None)
        return f"{res['meta']['estimated_duration_minutes']} minutes"

    @render.text
    async def code_savviness():
        res = await analysis_result()
        req(res is not None)
        return f"{res['meta']['percent_with_code']} %"

    @render.text
    async def image_presence():
        res = await analysis_result()
        req(res is not None)
        return f"{res['meta']['percent_with_images']} %"


app = App(app_ui, server)
