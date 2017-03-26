from PIL import Image, ImageDraw, ImageFont
from argparse import ArgumentParser
from psycopg2 import connect
from sys import argv, exit
import math


def handle_program_arguments():
    parser = ArgumentParser()
    t = lambda n: abs(int(n))
    w = (0, 0, 0)
    parser.add_argument("--canvas-size", "-cs", default=500, type=t,
                        help="Amount of pixels the square canvas should be")
    parser.add_argument(dest="cog_id", type=t, help="The cog ID in the data" +
                        "base to create the image for")
    parser.add_argument("--font-size", "-fs", default=11, type=t,
                        help="The size of the font the la" +
                        "bels are written with")
    parser.add_argument("--line-width", "-lw", default=2, type=t,
                        help="The width of the lines")
    parser.add_argument("--background-color", "-bc", type=t, nargs=3,
                        default=(255, 255, 255), choices=range(256),
                        help="The color of the background", metavar='0-255')
    parser.add_argument("--label-color", "-lc", default=w, choices=range(256),
                        help="The color of the label text", type=t,
                        metavar='0-255')
    parser.add_argument("--hit-color", "-hc", default=w, type=t, nargs=3,
                        choices=range(256), metavar='0-255',
                        help="The color of a line for a existing bidirectio" +
                        "nal hit")
    parser.add_argument("--theoretical-color", "-tc", default=(255, 0, 0),
                        type=t, nargs=3, help="The color of a line for a no" +
                        "t existing bidirectional hit", choices=range(256),
                        metavar='0-255')
    parser.add_argument("--output-file", "-o",
                        help="The file to save the image in")
    options = parser.parse_args()
    for attr in ("background_color", "label_color", "hit_color",
                 "theoretical_color"):
        setattr(options, attr, tuple(getattr(options, attr)))
    return options


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


def draw_label(opts, draw, point, radians, label, font):
    if radians < 0.5 * math.pi or radians > 1.5 * math.pi:
        point[0] += 5
    elif radians > 0.5 * math.pi or radians < 1.5 * math.pi:
        point[0] -= 5 + font.getsize(label)[0]
    if radians < math.pi:
        point[1] -= 10
    elif math.pi < radians < 2 * math.pi:
        point[1] += 10 - opts.font_size
    draw.text(tuple(point), label, fill=opts.label_color, font=font)


def get_and_draw_protein_points(opts, draw, proteins, radius, font):
    center_point = math.floor(opts.canvas_size / 2)
    point_map = dict()
    circle_step = 2 / len(proteins)
    for i in range(0, len(proteins)):
        radians = (i + 1) * circle_step * math.pi
        x = math.floor(abs(radius * math.cos(radians) + center_point) + 0.5)
        y = math.floor(abs(radius * math.sin(radians) - center_point) + 0.5)
        point_map[proteins[i]] = (x, y)
        draw_label(opts, draw, [x, y], radians, str(proteins[i]), font)
    return point_map


def draw_connections(draw, real_hits, point_map, theoretic_hits=[],
                     color=(0, 0, 0), line_width=2):
    for protein_a, protein_b in real_hits:
        point_list = [point_map[protein_a], point_map[protein_b]]
        draw.line(point_list, fill=color, width=line_width)
        for hit in [(protein_a, protein_b), (protein_b, protein_a)]:
            if hit in theoretic_hits:
                theoretic_hits.remove(hit)


def generate_cog_visualisation(opts, proteins, protein_hits):
    image = Image.new("RGB", (opts.canvas_size,) * 2,
                      color=opts.background_color)
    font = ImageFont.truetype("Vera.ttf", size=opts.font_size)
    text_width = 2 * max(map(lambda n: font.getsize(str(n))[0], proteins))
    drawing_instance = ImageDraw.Draw(image)
    protein_point_map = get_and_draw_protein_points(
        opts, drawing_instance, proteins,
        (opts.canvas_size - opts.font_size - text_width) / 2, font)
    all_hits = []
    for index in range(len(proteins)):
        for combine_with in proteins[index + 1:]:
            all_hits.append((proteins[index], combine_with))
    draw_connections(drawing_instance, protein_hits, protein_point_map,
                     theoretic_hits=all_hits, color=opts.hit_color,
                     line_width=opts.line_width)
    draw_connections(drawing_instance, all_hits, protein_point_map,
                     color=opts.theoretical_color, line_width=opts.line_width)
    image.save(opts.output_file or "{}.png".format(opts.cog_id), "PNG")


def main():
    options = handle_program_arguments()
    cog_proteins, cog_protein_hits = get_cog_data(options.cog_id)
    generate_cog_visualisation(options, cog_proteins, cog_protein_hits)


main()
