from dotenv import load_dotenv
from shiny import App, ui
from chatlas import ChatAnthropic

load_dotenv()  # Loads key from the .env file

# Define UI
app_ui = ui.page_fluid(
    ui.h1("DeckCheck"),
    # Card with chat component
    ui.card(
        ui.card_header("Get started"),
        ui.p("Ask me anything about your presentation 💡"),
        # Chat component
        ui.chat_ui(id="my_chat"),
    ),
)


# Define server
def server(input, output, session):
    chat_component = ui.Chat(id="my_chat")

    chat = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        system_prompt="You are a presentation coach for data scientists. You give constructive, focused, and practical feedback on titles, structure, and storytelling.",
    )

    @chat_component.on_user_submit
    async def handle_user_input(user_input: str):
        response = await chat.stream_async(user_input)
        await chat_component.append_message_stream(response)


# Create app
app = App(app_ui, server)
