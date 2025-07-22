library(shiny)
library(bslib)

ui <- page_fluid(
  theme = bs_theme(bootswatch = "minty"),

  # App title
  h1("DeckCheck"),

  # Create a card
  card(
    card_header("Welcome"),
    p("This is a simple Shiny app using bslib for layout and styling."),

    # Input: Slider
    textAreaInput("text", "What's your question?"),

    # Output: echo the text back
    textOutput("echo")
  )
)

server <- function(input, output, session) {
  # Reactive output
  output$echo <- renderText({
    paste("You asked:", input$text)
  })
}

shinyApp(ui, server)
