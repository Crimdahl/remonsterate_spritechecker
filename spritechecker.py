import os
import datetime
from PIL import Image, ImageOps
from collections import Counter

exe_directory = os.getcwd()
try:
    log_file = open("SpriteCheckerLog.txt", "a+")
except IOError as e:
    print("Error using log file: " + str(e))
count_total_sprites = 0
count_sprites_unchanged = 0
count_sprites_color_reduced = 0
count_sprites_mode_changed = 0
count_sprites_expanded = 0
count_sprites_cropped = 0

list_sprites_unchanged = []
list_sprites_color_reduced = []
list_sprites_mode_changed = []
list_sprites_expanded = []
list_sprites_cropped = []


def main():
    global exe_directory
    global log_file
    global count_total_sprites
    global count_sprites_unchanged
    global count_sprites_color_reduced
    global count_sprites_expanded
    global count_sprites_cropped
    global count_sprites_mode_changed
    global list_sprites_unchanged
    global list_sprites_color_reduced
    global list_sprites_mode_changed
    global list_sprites_expanded
    global list_sprites_cropped

    try:
        # Populate the file name lists. Iterates through directories starting at the
        #   directory containing the exe file. Does not traverse directories past
        #   the depth specified by walk_distance.
        walk_distance = 6
        exe_directory_level = exe_directory.count(os.path.sep)
        log("Looking for and analyzing png files in " + exe_directory + " and " + str(walk_distance) +
            " levels of sub-directories.")
        for root, dirs, files in os.walk(exe_directory):
            current_walking_directory = os.path.abspath(root)
            if "backup" in current_walking_directory:
                continue
            current_directory_level = current_walking_directory.count(os.path.sep)
            if current_directory_level > exe_directory_level + walk_distance:
                # del dirs[:] empties the list that os.walk uses to determine what
                #   directories to walk through, meaning os.walk will move on to
                #   the next directory. It does NOT delete or modify files on the
                #   hard drive.
                if len(dirs) > 0:
                    log("There were additional unexplored directories in " + current_walking_directory + ".")
                del dirs[:]
            else:
                for file_name in files:
                    if file_name.lower().endswith(".png"):
                        count_total_sprites = count_total_sprites + 1
                        check_image(Image.open(os.path.join(current_walking_directory, file_name)),
                                    current_walking_directory)
        log("Total sprites found: " + str(count_total_sprites))
        log("Total sprites unchanged: " + str(count_sprites_unchanged))
        log("Count of sprites that had too many colors: " + str(count_sprites_color_reduced))
        log("Count of sprites that had their mode converted: " + str(count_sprites_mode_changed))
        log("Count of sprites that were adjusted for efficiency: " +
            str(count_sprites_cropped + count_sprites_expanded) + '\n')

        index = 1
        input("Press any key to display a list of sprites that needed no adjustment.")
        log("Sprites that were unchanged:")
        for sprite in list_sprites_unchanged:
            log(str(index) + ': ' + sprite)
            index = index + 1
        index = 1
        log('')

        input("Press any key to display a list of sprites that had too many colors.")
        log("Sprites that had too many colors:")
        for sprite in list_sprites_color_reduced:
            log(str(index) + ': ' + sprite)
            index = index + 1
        index = 1
        log('')

        input("Press any key to display a list of sprites that were converted to be palettised.")
        log("Sprites that had their mode converted:")
        for sprite in list_sprites_mode_changed:
            log(str(index) + ': ' + sprite)
            index = index + 1
        index = 1
        log('')

        input("Press any key to display a list of sprites that were cropped/padded for FF6 efficiency.")
        log("Count of sprites that were adjusted for efficiency:")
        for sprite in (list_sprites_cropped + list_sprites_expanded):
            log(str(index) + ': ' + sprite)
            index = index + 1
        log('')
    except Exception as e2:
        log("Exception encountered: " + str(e2))
    finally:
        log_file.close()


def get_transparency(image: Image):
    width, height = image.size
    border = (
            [image.getpixel((0, j)) for j in range(height)] +
            [image.getpixel((width - 1, j)) for j in range(height)] +
            [image.getpixel((i, 0)) for i in range(width)] +
            [image.getpixel((i, height - 1)) for i in range(width)])
    transparency = Counter(border).most_common(1)[0][0]
    return transparency


def check_image(image: Image, current_directory: str):
    global exe_directory
    global count_sprites_unchanged
    global count_sprites_color_reduced
    global count_sprites_expanded
    global count_sprites_cropped
    global count_sprites_mode_changed
    global list_sprites_unchanged
    global list_sprites_color_reduced
    global list_sprites_mode_changed
    global list_sprites_expanded
    global list_sprites_cropped

    image_filename = image.filename
    image_filename_short = image_filename[len(exe_directory) + 1:]
    allowed_colors = 16
    current_colors = len(image.getcolors())
    image_changed = False

    # Detect images that aren't Palettised. These will be converted later.
    if image.mode != "P":
        count_sprites_mode_changed = count_sprites_mode_changed + 1
        list_sprites_mode_changed.append(image_filename_short)
        # log('Image will be converted to Mode P (palettised): ' + image_filename)

    # Check if the image has too many colors.
    if current_colors > allowed_colors:
        count_sprites_color_reduced = count_sprites_color_reduced + 1
        list_sprites_color_reduced.append(image_filename_short)
        # log('Image has too many colors, ' + str(current_colors) + ', and will be reduced: ' + image_filename)
        # If the image is already palettised, convert to RGBA so it can be re-palettised
        if image.mode == "P":
            image = image.convert("RGBA")

    # Convert non-palettised images and restrict their available colors
    if image.mode != "P":
        image = image.convert("P", palette=Image.ADAPTIVE, colors=allowed_colors)
        image_changed = True

    # Check if the top row and left column of the image are excess border
    image = image.convert('RGBA')
    border_color = get_transparency(image)
    solid_top = True
    solid_left = True
    had_transparent_border = False

    image_width_in_pixels, image_height_in_pixels = image.size
    while solid_top:
        current_color = border_color
        for x in range(image_width_in_pixels):
            # Scan the top row of pixels, cropping out the row if it is fully transparent
            if not current_color == image.getpixel((x, 0)):
                solid_top = False
            if not solid_top:
                break
            if x == image_width_in_pixels - 1 and solid_top:
                # If the top row was fully transparent, crop it out
                had_transparent_border = True
                image = image.crop((0, 1, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size

    while solid_left:
        current_color = border_color
        for y in range(image_height_in_pixels):
            # Scan the left column of pixels, cropping out the column if it is fully transparent
            if not current_color == image.getpixel((0, y)):
                solid_left = False
            if not solid_left:
                break
            if y == image_height_in_pixels - 1 and solid_left:
                # If the left column was fully transparent, crop it out
                had_transparent_border = True
                image = image.crop((1, 0, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size

    if had_transparent_border:
        # log('Cropped extra border space: ' + image_filename + '.')
        image_changed = True
        count_sprites_cropped = count_sprites_cropped + 1
        list_sprites_cropped.append(image_filename_short)

    # Tiles are 8x8, so we ensure the image's width and height are divisible by 8
    image_width_in_pixels, image_height_in_pixels = image.size
    image_expanded = False
    if not image_width_in_pixels % 8 == 0:
        image_changed = True
        image_expanded = True
        border_width = 8 - (image_width_in_pixels % 8)
        image = ImageOps.expand(image, border=(0, 0, border_width, 0), fill=border_color)

    if not image_height_in_pixels % 8 == 0:
        image_changed = True
        image_expanded = True
        border_width = 8 - (image_height_in_pixels % 8)
        image = ImageOps.expand(image, border=(0, 0, 0, border_width), fill=border_color)

    if image_expanded:
        count_sprites_expanded = count_sprites_expanded + 1
        list_sprites_expanded.append(image_filename_short)
        # log('Expanded to fill an 8x8 tile: ' + image_filename)

    if image_changed:
        # Move the old file to a backup location
        image.filename = image_filename
        image = image.convert("P", palette=Image.ADAPTIVE, colors=allowed_colors)
        backup_location = os.path.join(exe_directory,
                                       "backup",
                                       current_directory[len(exe_directory) + 1:],
                                       image_filename[len(current_directory) + 1:])
        os.makedirs(os.path.dirname(backup_location), exist_ok=True)
        os.replace(src=image_filename, dst=backup_location)
        image.save(image_filename)
        # pass
    else:
        count_sprites_unchanged = count_sprites_unchanged + 1
        list_sprites_unchanged.append(image_filename_short)


def log(line):
    # Log to both console and file
    global log_file
    print(line)
    if log_file:
        log_file.writelines(str(datetime.datetime.now()) + " " + line + "\n")


if __name__ == '__main__':
    try:
        print('This program will look through ALL .png files in the programs directory and up to 4 '
              'sub-directories.')
        print('If a sprite has more than 16 colors, it will be converted to use only 16 colors.')
        print('If a sprite has a excess border space on the top or left, it will be cropped.')
        print('If a sprite does not evenly fill an 8x8 tile, the bottom and/or right borders will be expanded.')
        print('The original image is saved in a backup directory in the script directory.')
        run_script = input('Continue? Y/N:  ')
        if run_script.lower() == "y":
            main()
        input("Press any key to exit.")
    except Exception as e:
        print(str(e))
        input("Press any key to exit.")
