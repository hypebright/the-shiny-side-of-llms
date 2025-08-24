from shiny import App, reactive, render, ui
import shinyswatch
import pandas as pd
import plotnine as p9

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


# Mock analysis result for demonstration since we don't have the LLM integration
def get_mock_analysis():
    return {
        "meta": {
            "presentation_title": "Sample Presentation",
            "total_slides": 25,
            "percent_with_code": 40.0,
            "percent_with_images": 60.0,
            "estimated_duration_minutes": 15,
            "tone": "Technical and informative",
        },
        "evals": pd.DataFrame(
            {
                "category": [
                    "clarity",
                    "relevance",
                    "visual_design",
                    "engagement",
                    "pacing",
                    "structure",
                    "consistency",
                    "accessibility",
                ],
                "score": [7, 8, 6, 5, 7, 8, 6, 7],
                "justification": [
                    "Clear explanations but some technical terms need definition",
                    "Content matches audience well",
                    "Good use of visuals but some slides are cluttered",
                    "Could benefit from more interactive elements",
                    "Well-paced overall with some dense sections",
                    "Logical flow with clear beginning and end",
                    "Mostly consistent formatting with minor variations",
                    "Good font sizes but could improve color contrast",
                ],
                "improvements": [
                    "Define technical terms on slide 3 and 7",
                    "Add more practical examples on slides 10-12",
                    "Reduce text density on slides 5 and 15",
                    "Add poll questions on slides 8 and 18",
                    "Split content on slide 20 into two slides",
                    "Add transition slides between sections",
                    "Standardize bullet point formatting",
                    "Increase contrast for text on slide backgrounds",
                ],
                "score_after_improvements": [9, 9, 8, 7, 8, 9, 8, 8],
            }
        ),
    }


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
                ui.TagList("🤖", " Analyse presentation"),
                class_="btn-primary",
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
                ui.TagList("👍", " Like"),
                class_="btn-success btn-sm",
                style="opacity: 0.75; margin-right: 10px;",
            ),
            ui.input_action_button(
                "dislike",
                ui.TagList("👎", " Dislike"),
                class_="btn-danger btn-sm",
                style="opacity: 0.75;",
            ),
            class_="d-flex p-2 gap-2",
        ),
    ),
    theme=shinyswatch.theme.flatly,
)


def server(input, output, session):
    # Reactive value to store analysis results
    analysis_result = reactive.value(None)

    # Mock the analysis process when submit is clicked
    @reactive.effect
    @reactive.event(input.submit)
    def analyze_presentation():
        # In a real implementation, this would process the uploaded file
        # and call the LLM for analysis
        if input.file() is not None:
            # For demo purposes, use mock data
            result = get_mock_analysis()
            analysis_result.set(result)

    @render.plot
    def scores():
        if analysis_result() is None:
            return None

        evals = analysis_result()["evals"].copy()
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
    def suggested_improvements():
        if analysis_result() is None:
            return pd.DataFrame()

        evals = analysis_result()["evals"].copy()
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
    def showtime():
        if analysis_result() is None:
            return ""
        return f"{analysis_result()['meta']['estimated_duration_minutes']} minutes"

    @render.text
    def code_savviness():
        if analysis_result() is None:
            return ""
        return f"{analysis_result()['meta']['percent_with_code']} %"

    @render.text
    def image_presence():
        if analysis_result() is None:
            return ""
        return f"{analysis_result()['meta']['percent_with_images']} %"


app = App(app_ui, server)
