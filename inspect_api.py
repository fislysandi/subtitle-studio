
import bpy
import os

output_file = "api_dump.txt"

try:
    if bpy.context.scene.sequence_editor:
        se = bpy.context.scene.sequence_editor
        with open(output_file, "w") as f:
            f.write(f"Type: {type(se)}\n")
            f.write(f"Dir: {dir(se)}\n")
            # f.write(f"Sequences? {'sequences' in dir(se)}\n")
            # f.write(f"Sequences_all? {'sequences_all' in dir(se)}\n")
            # f.write(f"Strips? {'strips' in dir(se)}\n")
    else:
        with open(output_file, "w") as f:
            f.write("No SequenceEditor in context.scene\n")
except Exception as e:
    with open(output_file, "w") as f:
        f.write(f"Error: {e}\n")
