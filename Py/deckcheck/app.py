from shiny import App, reactive, render, ui, req
from shinywidgets import output_widget, render_widget
import shinyswatch
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from chatlas import ChatAnthropic, interpolate_file, interpolate
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Optional, Union
import tempfile
import shutil
import asyncio

load_dotenv()  # Loads key from the .env file

# Path to the current file
APP_DIR = Path(__file__).parent
# Root directory of the project
ROOT_DIR = APP_DIR.parent.parent

# ======================
# Data Structure
# ======================
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
    consistency: ScoringCategory = Field(  # spelling kept as-is
        ...,
        description="Evaluatue whether the presentation is consistent when it comes to formatting, tone, and visual elements. Are there any elements that feel out of place?",
    )
    accessibility: ScoringCategory = Field(
        ...,
        description="Consider how accessible the presentation would be for all viewers, including those with visual or cognitive challenges. Are font sizes readable? Is there sufficient contrast? Are visual elements not overwhelming?",
    )


# ======================
# Tool definition
# ======================
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


# ======================
# Data wrangling
# ======================
def make_frames(d: dict):
    """
    Convert the dictionary returned by the LLM into a meta dictionary and
    a DataFrame for the eval categories.
    Parameters
    ----------
    d : dict
        The dictionary returned by the LLM.

    Returns
    -------
    dict
        A dictionary with two keys: "meta" and "evals". "meta" contains the
        meta information as a dictionary, and "evals" contains a DataFrame with
        the eval categories.
    """
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
            evals.append(
                {
                    "category": k,
                    "score": v["score"],
                    "justification": v["justification"],
                    "improvements": v["improvements"],
                    "score_after_improvements": v["score_after_improvements"],
                }
            )

    evals_df = pd.DataFrame(evals)

    return {"meta": meta, "evals": evals_df}


# ======================
# Tooltip helper
# ======================
def add_line_breaks(text, width=50):
    if not isinstance(text, str):
        return text

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # +1 accounts for the space if current_line isn’t empty
        if len(current_line) + len(word) + (1 if current_line else 0) <= width:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return "<br>".join(lines)


# ======================
# Icons
# ======================
file_slides = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" class="bi bi-file-slides-fill" viewBox="0 0 16 16">
  <path d="M7 7.78V5.22c0-.096.106-.156.19-.106l2.13 1.279a.125.125 0 0 1 0 .214l-2.13 1.28A.125.125 0 0 1 7 7.778z"/>
  <path d="M12 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2M5 4h6a.5.5 0 0 1 .496.438l.5 4A.5.5 0 0 1 11.5 9h-3v2.016c.863.055 1.5.251 1.5.484 0 .276-.895.5-2 .5s-2-.224-2-.5c0-.233.637-.429 1.5-.484V9h-3a.5.5 0 0 1-.496-.562l.5-4A.5.5 0 0 1 5 4"/>
</svg>"""

file_slides_loader = """<svg xmlns="http://www.w3.org/2000/svg" width="6em" height="6em" fill="currentColor" class="bi bi-file-slides bounce" viewBox="0 0 16 16">
  <path d="M5 4a.5.5 0 0 0-.496.438l-.5 4A.5.5 0 0 0 4.5 9h3v2.016c-.863.055-1.5.251-1.5.484 0 .276.895.5 2 .5s2-.224 2-.5c0-.233-.637-.429-1.5-.484V9h3a.5.5 0 0 0 .496-.562l-.5-4A.5.5 0 0 0 11 4zm2 3.78V5.22c0-.096.106-.156.19-.106l2.13 1.279a.125.125 0 0 1 0 .214l-2.13 1.28A.125.125 0 0 1 7 7.778z"/>
  <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2zm10-1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1"/>
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

robot_loader = """<svg xmlns="http://www.w3.org/2000/svg" width="6em" height="6em" fill="currentColor" class="bi bi-robot text-primary bounce" viewBox="0 0 16 16">
  <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135"/>
  <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5"/>
</svg>"""

sad_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-emoji-frown-fill text-warning" viewBox="0 0 16 16">
  <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16M7 6.5C7 7.328 6.552 8 6 8s-1-.672-1-1.5S5.448 5 6 5s1 .672 1 1.5m-2.715 5.933a.5.5 0 0 1-.183-.683A4.5 4.5 0 0 1 8 9.5a4.5 4.5 0 0 1 3.898 2.25.5.5 0 0 1-.866.5A3.5 3.5 0 0 0 8 10.5a3.5 3.5 0 0 0-3.032 1.75.5.5 0 0 1-.683.183M10 8c-.552 0-1-.672-1-1.5S9.448 5 10 5s1 .672 1 1.5S10.552 8 10 8"/>
</svg>"""

# ======================
# Shiny App
# ======================
app_ui = ui.page_fillable(
    ## General theme and styles
    ## 1. Custom CSS
    ui.tags.style("""
        #suggested_improvements table {
            font-family: 'Lato', sans-serif;
            font-size: 11px;
        }
        .bounce {
            animation: bounce 2s infinite;
        }
        @keyframes bounce {
            0%, 100% {
                transform: translateY(0);
            }
            50% {
                transform: translateY(-20px);
            }
        }
    """),
    ui.layout_sidebar(
        ui.sidebar(
            ## Sidebar content
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
            ui.input_task_button(
                "submit",
                icon=ui.HTML(robot),
                label="Analyse presentation",
            ),
            width=400,
        ),
        ## Main content
        ui.output_ui("results"),
    ),
    # Bootswatch theme
    theme=shinyswatch.theme.flatly,
)


def server(input, output, session):
    @ui.bind_task_button(button_id="submit")
    @reactive.extended_task
    async def quarto_task(file_path, temp_dir):
        # We're using an Extended Task to avoid blocking. Note that
        # a temporary directory called within mirai will be
        # different from the one in the "main" Shiny session. Hence,
        # we pass a temp_dir parameter to the task and use that.
        qmd_file = Path(temp_dir) / "my-presentation.qmd"
        shutil.copy(file_path, qmd_file)

        # Run asyncio subprocess
        proc = await asyncio.create_subprocess_exec(
            "quarto", "render", str(qmd_file), "--to", "markdown,html"
        )
        await proc.communicate()

        # Return the path to the markdown file
        return Path(temp_dir) / "my-presentation.md"

    @ui.bind_task_button(button_id="submit")
    @reactive.extended_task
    async def chat_task(system_prompt, markdown_content, DeckAnalysis):
        # We're using an extended task to avoid blocking the session and
        # we start a fresh chat session each time.
        # For a feedback loop, we would use a persistent chat session.
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

        return chat_res2

    @reactive.effect
    @reactive.event(input.submit)
    async def run_quarto():
        req(input.file() is not None)
        try:
            # Error for testing
            # raise ValueError("Test error")

            # Get file path of the uploaded file
            file_path = input.file()[0]["datapath"]

            quarto_task.invoke(file_path, tempfile.gettempdir())

        except Exception as e:
            print(f"Error when trying to invoke quarto_task: {e}")

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

    @reactive.effect
    def run_chat():
        # require quarto_task result to be available
        req(quarto_task.result() is not None)
        try:
            # Error for testing
            # raise ValueError("Test error")

            # Get the Markdown file path from the complete quarto_task
            markdown_file = quarto_task.result()
            # Read the generated Markdown file containing the slides
            markdown_content = markdown_file.read_text(encoding="utf-8")

            # Define prompt file
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

            # Trigger the chat task with the provided inputs
            chat_task.invoke(system_prompt, markdown_content, DeckAnalysis)

        except Exception as e:
            print(f"Error when trying to invoke chat_task: {e}")

            # Return value that triggers modal in UI
            m = ui.modal(
                ui.div(
                    # Sad bootstrap icon
                    ui.HTML(sad_icon),
                    ui.br(),
                    ui.p(
                        "The not so Shiny Side of LLMs. Unfortunately, chatting didn't work out. Do you have enough credits left?"
                    ),
                    # add class to center the content
                    class_="text-center",
                ),
                title="Oops, something went wrong!",
                easy_close=True,
                footer=ui.modal_button("Close"),
            )
            ui.modal_show(m)

    @reactive.calc
    def analysis_result():
        res = chat_task.result()
        if res is not None:
            return make_frames(res)
        else:
            return None

    @render.ui
    async def results():
        if quarto_task.status() == "running":
            return ui.div(
                ui.HTML(file_slides_loader),
                ui.br(),
                ui.p("Processing your Quarto presentation..."),
                class_="text-center d-flex flex-column justify-content-center align-items-center",
                style="height: 100%",
            )

        elif chat_task.status() == "running":
            return ui.div(
                ui.HTML(robot_loader),
                ui.br(),
                ui.p("The LLM is doing its magic..."),
                class_="text-center d-flex flex-column justify-content-center align-items-center",
                style="height: 100%",
            )

        elif chat_task.status() == "success":
            return ui.TagList(
                ui.layout_column_wrap(
                    ui.tooltip(
                        ui.value_box(
                            "Showtime",
                            ui.output_text("showtime"),
                            showcase=ui.HTML(file_slides),
                            theme="primary",
                        ),
                        "Slides are being counted based on the provided Quarto presentation, then an educated guess is made about the time it will take to present them.",
                    ),
                    ui.tooltip(
                        ui.value_box(
                            "Code Savviness",
                            ui.output_text("code_savviness"),
                            showcase=ui.HTML(file_code),
                            theme="primary",
                        ),
                        "Code Saviness is calculated based on the slides that contain code chunks. The percentage is the ratio of those slides to total slides.",
                    ),
                    ui.tooltip(
                        ui.value_box(
                            "Image Presence",
                            ui.output_text("image_presence"),
                            showcase=ui.HTML(file_image),
                            theme="primary",
                        ),
                        "Image Presence is calculated based on the slides that contain images. The percentage is the ratio of those slides to total slides.",
                    ),
                    width=1 / 3,
                    fill=False,
                ),
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header(ui.strong("Scores per category")),
                        output_widget("scores"),
                        height="600px",
                    ),
                    ui.card(
                        ui.card_header(
                            ui.strong("Suggested improvements per category")
                        ),
                        ui.output_data_frame("suggested_improvements"),
                        height="600px",
                    ),
                    width=1 / 2,
                    fill=False,
                ),
            )

    @render_widget
    def scores():
        res = analysis_result()

        req(res is not None)

        evals = res["evals"].copy()
        evals = evals.sort_values("score")
        evals["category"] = pd.Categorical(
            evals["category"], categories=evals["category"], ordered=True
        )

        # apply to the justification column
        evals["justification_wrapped"] = evals["justification"].apply(add_line_breaks)

        # Create a custom tooltip column
        evals["tooltip"] = (
            "Score: "
            + evals["score"].astype(str)
            + "<br>After improvements: "
            + evals["score_after_improvements"].astype(str)
            + "<br>Justification: "
            + evals["justification_wrapped"]
        )

        plot = px.bar(
            evals,
            x="score",
            y="category",
            orientation="h",
            labels={"category": "Category", "score": "Score"},
            hover_data={"tooltip": True},  # include the tooltip column
        )

        # Set hovertemplate to use our custom tooltip
        plot.update_traces(
            hovertemplate="%{customdata[0]}<extra></extra>",
            customdata=evals[["tooltip"]].values,
        )

        plot.update_traces(marker_color="#18bc9c")

        plot.update_layout(template="simple_white")

        return plot

    @render.data_frame
    def suggested_improvements():
        res = analysis_result()

        req(res is not None)

        evals = res["evals"].copy()
        evals["Gain"] = evals["score_after_improvements"] - evals["score"]

        result_table = evals.assign(
            Category=evals["category"],
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
    def showtime():
        res = analysis_result()

        req(res is not None)
        return f"{res['meta']['estimated_duration_minutes']} minutes"

    @render.text
    def code_savviness():
        res = analysis_result()
        req(res is not None)
        return f"{res['meta']['percent_with_code']} %"

    @render.text
    def image_presence():
        res = analysis_result()
        req(res is not None)
        return f"{res['meta']['percent_with_images']} %"


app = App(app_ui, server)
