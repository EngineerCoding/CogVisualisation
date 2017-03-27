from PIL import Image, ImageDraw, ImageFont
from argparse import ArgumentParser
from psycopg2 import connect
from sys import exit
import math


def handle_program_arguments():
    """ This function will use the argparse.ArgumentParser to retrieve
    options from the command line. Those options are as follows:
    usage: visualise_cog.py [-h] [--canvas-size CANVAS_SIZE]
                            [--font-size FONT_SIZE]
                            [--line-width LINE_WIDTH]
                            [--background-color 0-255 0-255 0-255]
                            [--label-color 0-255]
                            [--hit-color 0-255 0-255 0-255]
                            [--theoretical-color 0-255 0-255 0-255]
                            [--output-file OUTPUT_FILE]
                            cog_id

    positional arguments (required):
      cog_id                The cog ID in the database to create the
                            image for

    optional arguments:
      -h, --help            show this help message and exit
      --canvas-size CANVAS_SIZE, -cs CANVAS_SIZE
                            Amount of pixels the square canvas should
                            be
      --font-size FONT_SIZE, -fs FONT_SIZE
                            The size of the font the labels are
                            written with
      --line-width LINE_WIDTH, -lw LINE_WIDTH
                            The width of the lines
      --background-color 0-255 0-255 0-255, -bc 0-255 0-255 0-255
                            The color of the background
      --label-color 0-255, -lc 0-255
                            The color of the label text
      --hit-color 0-255 0-255 0-255, -hc 0-255 0-255 0-255
                            The color of a line for a existing
                            bidirectional hit
      --theoretical-color 0-255 0-255 0-255, -tc 0-255 0-255 0-255
                            The color of a line for a not existing
                            bidirectional hit
      --output-file OUTPUT_FILE, -o OUTPUT_FILE
                            The file to save the image in
    Returns:
        A name argparse.Namespace object which is parsed from sys.argv.
    """
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
    """ Retrieves the data required to generate the COG with. This data
    is is split into two sets: 1 set for all proteins in the COG and
    the other contains the connection data between those proteins.
    Parameters:
        cog_id (int): A COG id which lives in the database.
    Returns:
        A list of protein ids which are in the specified COG. Also
        returns a list of bidirectional hits betweeen the proteins in
        the specified COG.
    """
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
    """ This method will move the point a bit based on the radians,
    with the unit circle in mind. Then it will draw the label name
    using the given font and color settings.
    Parameters:
        opts (argparse Namespace): The options given with the
            execution of this program.
        draw (PIL.DrawImage.Draw instance): The drawing instance
            which should be drawn to.
        point (list of ints): A [x, y] list to represent the point of
            the label.
        radians (decimal): The calculated radians for this point.
        label (string): The string to draw as label.
        font (PIL.ImageFont): The font which is used to draw the label.
    """
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
    """ Calculates the points of the all the proteins in the COG. This
    is done by using the theorem of the unit circle. Those positions
    from the sinus and cosinus are based a regular axes, it has to
    be translated to the axis as defined in the PIL library. This is
    done by moving the y axis and x axis appropriately.
    The calculated points are stored in a dictionary with as key the
    protein id along the value as a (x, y) tuple.

    Parameters:
        opts (argparse Namespace): The options given with the
            execution of this program.
        draw (PIL.DrawImage.Draw instance): The drawing instance
            which should be drawn to.
        proteins (list of ints): All the protein ids in a list which
            are contained by the specified COG.
        radius (int): The calculated radius for this canvas size and
            font size.
        font (PIL.ImageFont): The font which is used to draw the label.
    Returns:
        The dictionary containing (x, y) tuples as values which are
        retrieved by using a protein id as key.
    """
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
    """ Draws the existing connections from the real_hits list using
    the point_map as point reference. Hits which are being drawn, are
    removed from the theoretic_hits to identify missing hits.

    Parameters:
        draw (PIL.DrawImage.Draw instance): The drawing instance
            which should be drawn to.
        real_hits (list of tuples): A list of tuples which contain
            the real connections between proteins.
        point_map (dictionary): The dictionary containing (x, y) tuples
            as values which are retrieved by using a protein id as key.
        theoretic_hits (list of tuples): A list where drawn hits
            should be removed from, to for instance draw missing hits.
        color (RGB tuple): The color to use to draw the line.
        line_width (int): The width of the line which is drawn.
    """
    for protein_a, protein_b in real_hits:
        point_list = [point_map[protein_a], point_map[protein_b]]
        draw.line(point_list, fill=color, width=line_width)
        for hit in [(protein_a, protein_b), (protein_b, protein_a)]:
            if hit in theoretic_hits:
                theoretic_hits.remove(hit)


def generate_cog_visualisation(opts, proteins, protein_hits):
    """ The main method of generating the COG image. This image is
    generated with the given program settings in mind given through
    the CLI.
    This will create a blank image, calculate the radius for the used
    circle and draws the real and missing connection between the
    proteins.

    Parameters:
        opts (argparse Namespace): The options given with the
            execution of this program.
        proteins (list of ints): All the protein ids in a list which
            are contained by the specified COG.
        protein_hits (list of tuples): A list of tuples which contain
            the real connections between proteins.
    """
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
