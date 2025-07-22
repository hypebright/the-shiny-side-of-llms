from shiny import App, ui, render

# Define UI
app_ui = ui.page_fluid(
    ui.h1("Simple Shiny App"),
    # Card with slider
    ui.card(
        ui.card_header("Welcome"),
        ui.p("This is a basic Shiny for Python application."),
        # Input: Slider
        ui.input_text_area("text", "What's your question?"),
        # Output: echo text back
        ui.output_text("echo"),
    ),
)


# Define server
def server(input, output, session):
    @render.text
    def echo():
        return f"You asked: {input.text()}"


# Create app
app = App(app_ui, server)
