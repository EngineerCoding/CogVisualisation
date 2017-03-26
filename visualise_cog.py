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
        system(executable + " -m pip install pillow")
        print("Restart this script")
        exit()
    print("pillow dependency not found")
    exit(-1)


def to_number(argument_name, value):
    if value.strip().isnumeric():
        return int(value.strip())
    print("Invalid argument for {} with \"{}\"".format(argument_name, value))
    exit()


def expected_cog_number():
    print("Expected cog number")
    exit()


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
    if radians < 0.5 * math.pi or radians > 1.5 * math.pi:
        point[0] += 5
    elif radians > 0.5 * math.pi or radians < 1.5 * math.pi:
        point[0] -= 5 + font.getsize(label)[0]
    if radians < math.pi:
        point[1] -= 10
    elif math.pi < radians < 2 * math.pi:
        point[1] += 10
    draw.text(tuple(point), label, fill=(0, 0, 0))


def get_and_draw_protein_points(draw, proteins, radius, canvas_size, font):
    center_point = math.floor(canvas_size / 2)
    point_map = dict()
    circle_step = 2 / len(proteins)
    for i in range(0, len(proteins)):
        radians = (i + 1) * circle_step * math.pi
        x = math.floor(abs(radius * math.cos(radians) + center_point) + 0.5)
        y = math.floor(abs(radius * math.sin(radians) - center_point) + 0.5)
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
    image = Image.new("RGB", (canvas_size, canvas_size), color=(255, 255,
                                                                255))
    font = ImageFont.load_default()
    text_width = 2 * max(map(lambda n: font.getsize(str(n))[0], proteins))
    drawing_instance = ImageDraw.Draw(image)
    protein_point_map = get_and_draw_protein_points(
        drawing_instance, proteins, (canvas_size - 10 - text_width) / 2,
        canvas_size, font)
    all_hits = []
    for index in range(len(proteins)):
        for combine_with in proteins[index + 1:]:
            all_hits.append((proteins[index], combine_with))
    draw_connections(drawing_instance, protein_hits, protein_point_map,
                     theoretic_hits=all_hits)
    draw_connections(drawing_instance, all_hits, protein_point_map,
                     color=(255, 0, 0))
    image.save(output_file, "PNG")


def main():
    cog_id, canvas_size = handle_program_arguments()
    cog_proteins, cog_protein_hits = get_cog_data(cog_id)
    generate_cog_visualisation(cog_proteins, cog_protein_hits, canvas_size,
                               str(cog_id) + ".png")


main()
