from shiny import App, Inputs, Outputs, Session, reactive, render, ui

items = [
    ui.accordion_panel(f"Section {letter}", f"Some narrative for section {letter}")
    for letter in "ABCDE"
]

# # First shown by default
# ui.accordion(*items)

# # Nothing shown by default
# ui.accordion(*items, open=False)
# # Everything shown by default
# ui.accordion(*items, open=True)

# # Show particular sections
# ui.accordion(*items, open="Section B")
# ui.accordion(*items, open=["Section A", "Section B"])


app_ui = ui.page_fluid(
    # Provide an id to create a shiny input binding
    ui.accordion(*items, id="acc"),
    ui.h4("Accordion:"),
    ui.output_text_verbatim("acc_val", placeholder=True),
)


def server(input: Inputs, output: Outputs, session: Session):
    @reactive.Effect
    def _():
        print(input.acc())

    @output
    @render.text
    def acc_val():
        return input.acc()


app = App(app_ui, server)