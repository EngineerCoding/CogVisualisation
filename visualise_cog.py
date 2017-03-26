from sys import argv, exit
from psycopg2 import connect
import math
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    from sys import executable
    from os import system
    if (input("Do you want to install the pillow dependency? (y/n)")
            .strip().lower() == "y"):
        os.system(executable + " -m pip install pillow")
        print("Restart this script")
        sys.exit()
    print("pillow dependency not found")
    sys.exit(-1)


def to_number(argument_name, value):
    if value.strip().isnumeric():
        return int(argv[index + 1].strip())
    print("Invalid argument for {} with \"{}\"".format(argument_name, value))
    sys.exit()


def expected_cog_number():
    print("Expected cog number")
    sys.exit()

def handle_program_arguments():
    del argv[0]
    if len(argv) == 0:
        expected_cog_number()
    cog_id = to_number("COG", argv[-1])
    canvas_size = 500
    if "--size" in argv:
        index = argv.index("--size")
        if index == len(argv) - 1:
            expected_cog_number()
        if index + 1 < len(argv):
            canvas_size = to_number("--size", argv[index + 1])
    return abs(cog_id), abs(canvas_size)


def get_cog_data(cog_id):
    connection = connect(host="localhost", dbname="postgres", user="postgres",
                         password="Password")
    cursor = connection.cursor()
    cursor.execute("SELECT protein_id FROM protein WHERE cog = %s", (cog_id,))
    cog_proteins = tuple(map(lambda n: n[0], cursor.fetchall()))
    cursor.execute("""SELECT protein_a, protein_b
                      FROM directionalhit
                      WHERE protein_a IN {p} AND protein_b IN {p}
                   """.format(p=str(cog_proteins)))
    cog_protein_hits = cursor.fetchall()
    cursor.close()
    connection.close()
    return cog_proteins, cog_protein_hits


def draw_label(draw, point, radians, label, font):
    label_width = font.getsize(label)
    point[0] = (point[0] - label_width - 5
                if 0.5 * math.pi < radians < 1.5 * math.pi else point[0] + 5)
    point[1] = point[1] + 2 if radians < math.pi else point[1] - 2
    if radians % math.pi == 0.0:
        point[1] += 2
    elif radians % 0.5 * math.pi == 0.0:
        point[0] -= 5 + floor(label_width / 2)
    draw.text(tuple(point), label)


def get_and_draw_protein_points(draw, proteins, radius, canvas_size, font):
    center_point = floor(canvas_size / 2)
    point_map = dict()
    circle_step = 2 / len(proteins)
    for i in range(1, len(proteins) + 1):
        radians = i * circle_step * math.pi
        x = abs(radius * math.cos(radians) - center_point)
        y = abs(radius * math.sin(radians) - center_point)
        point_map[proteins[i]] = (x, y)
        draw_label(draw, [x, y], radians, str(proteins[i]), font)
    return point_map


def draw_connections(draw, real_hits, point_map, theoretic_hits=[],
                     color=(0, 0, 0)):
    for protein_a, protein_b in real_hits:
        point_list = [point_map[protein_a], point_map[protein_b]]
        draw.line(point_list, fill=color, width=2)
        for hit in [(protein_a, protein_b), (protein_b, protein_a)]:
            if hit in theoretic_hits:
                theoretic_hits.remove(hit)


def generate_cog_visualisation(proteins, protein_hits, canvas_size,
                               output_file):
    image = Image.new("RGB", (canvas_size, canvas_size))
    font = ImageFont.load_default()
    max_text_width = max(map(lambda n: font.getsize(str(n)), proteins))
    drawing_instance = ImageDraw.new(image)
    protein_point_map = get_and_draw_protein_points(
        drawing_instance, proteins, canvas_size - 10 - max_text_width,
        canvas_size, font)
    all_hits = []
    for index in range(len(proteins)):
        for combine_with in proteins[index + 1:]:
            all_hits.append((proteins[index], combine_with))
    draw_connections(drawing_instance, protein_hits, protein_point_map,
                     theoretic_hits=all_hits)
    draw_connections(drawing_instance, all_hits, protein_point_map,
                     color=(255, 0, 0))


def main():
    cog_id, canvas_size = handle_program_arguments()
    cog_proteins, cog_protein_hits = get_cog_data(cog_id)
    generate_cog_visualisation(cog_proteins, cog_protein_hits, canvas_size,
                               str(cog_id) + ".png")
