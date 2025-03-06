from typing import List, Literal
from pydantic import BaseModel, Field
import logging
import json

# agents
from agents.writer import writer
from agents.editor import editor

# For simplicity, removed other agents like researcher, product, etc.

types = Literal["message", "writer", "editor", "error", "partial"]

class Message(BaseModel):
    type: types
    message: str | dict | None
    data: List | dict = Field(default={})

    def to_json_line(self):
        return self.model_dump_json().replace("\n", "") + "\n"

DEFAULT_LOG_LEVEL = 25

def log_output(*args):
    logging.log(DEFAULT_LOG_LEVEL, *args)

def start_message(type: types):
    return Message(
        type="message", message=f"Starting {type} agent task..."
    ).to_json_line()

def complete_message(type: types, result):
    return Message(
        type=type, message=f"Completed {type} task", data=result
    ).to_json_line()

def error_message(error: Exception):
    return Message(
        type="error", message="An error occurred.", data={"error": str(error)}
    ).to_json_line()

def send_writer(full_result):
    return json.dumps(("writer", full_result))

def send_editor(editor_result):
    return json.dumps(("editor", editor_result))

def building_agents_message():
    return Message(
        type="message", message=f"Initializing Writer and Editor Services, please wait a few seconds..."
    ).to_json_line()

@trace
def create(research_context, product_context, assignment_context, feedback="No Feedback"):

    yield building_agents_message()

    # Start writer task
    yield start_message("writer")
    writer_result = writer.write(
        research_context, research_context, product_context, product_context, assignment_context, feedback
    )

    full_result = ""
    for item in writer_result:
        full_result += f'{item}'
        yield complete_message("partial", {"text": item})

    processed_writer_result = writer.process(full_result)

    # Start editor task
    yield start_message("editor")
    editor_response = editor.edit(processed_writer_result['article'], processed_writer_result["feedback"])
    yield complete_message("editor", editor_response)

    # After editor feedback, check decision
    if str(editor_response["decision"]).lower().startswith("accept"):
        yield ("message", "Editor accepted the article.")
    else:
        yield ("message", "Editor rejected the article.")

    # Send results
    yield send_writer(full_result)
    yield send_editor(editor_response)

@trace  
def test_create_article(research_context, product_context, assignment_context):
    for result in create(research_context, product_context, assignment_context):
        parsed_result = json.loads(result)
        if type(parsed_result) is dict:
            if parsed_result['type'] == 'writer':
                print(f"Writer Result: {parsed_result['data']}")
            if parsed_result['type'] == 'editor':
                print(f"Editor Feedback: {parsed_result['data']}")
    
if __name__ == "__main__":
    local_trace = PromptyTracer()
    Tracer.add("PromptyTracer", local_trace.tracer)
    research_context = "Can you find the latest trends in outdoor camping?"
    product_context = "Can you recommend camping gear like tents and sleeping bags?"
    assignment_context = '''Write an article about camping trends, focusing on winter camping, with product recommendations for gear.'''

    test_create_article(research_context=research_context, product_context=product_context, assignment_context=assignment_context)
