library(shiny)
library(bslib)
library(ellmer)
library(shinychat)

ui <- page_fluid(
  theme = bs_theme(bootswatch = "minty"),

  # App title
  h1("DeckCheck"),

  # Create a card
  card(
    card_header("Get started"),
    p("Ask me anything about your presentation 💡"),

    # Chat component
    chat_mod_ui("chat_component")
  )
)

server <- function(input, output, session) {
  chat <- chat_anthropic(
    model = "claude-sonnet-4-20250514",
    system_prompt = "You are a presentation coach for data scientists. 
  You give constructive, focused, and practical feedback on titles, structure, and storytelling."
  )

  chat_mod_server("chat_component", chat)
}

shinyApp(ui, server)
