# -*- coding: utf-8 -*-


import sys
import codecs
import re
import os
import glob

from rapidfuzz import process
from rapidfuzz.distance import Levenshtein


def main():
    """ Output result.txt file including similarities to database """
    input_dir_path = sys.argv[1]
    num_moves = int(sys.argv[2])
    #input_dir_path = os.getcwd()
    #num_moves = 20

    # paths of database and query sgf file
    database_path = os.path.normpath(".\database")
    query_sgf_path = os.path.normpath(input_dir_path + "\\test.sgf")

    # make database
    path_list = glob.glob(os.path.normpath(database_path + "\\*"))
    database = make_database_list(path_list, num_moves)

    # make 16-type variations of moves from query sgf
    query_moves = read_query_sgf(query_sgf_path, num_moves)

    # Calculate similarity
    similarity = calc_similarity(query_moves, database)

    # re-sorted database by similarity in decreasing order
    temp = [[str1, var1] for str1, var1 in zip(path_list, similarity)]
    result = sorted(temp, key = lambda x: x[1], reverse = True)

    # output result.txt
    output_file_path = os.path.normpath(input_dir_path + "\\result.txt")

    with codecs.open(output_file_path, 'w', encoding = 'utf-8') as output_file:
        for i in range(len(result)):
            print(f"{result[i][0]}, {result[i][1]}", file = output_file)



##### Make kifu database list #####

def make_database_list(path_list, num_moves = 500):
    """ make database lists from sgf files """
    database_list = []
    for input_sgf_path in path_list:
        # read moves from sgf to list-type
        moves = sgf_to_list(input_sgf_path, num_moves)
        
        # convert moves from UPPER to lower
        moves_lower = convert_lower(moves)
        
        database_list.append(moves_lower)
    return database_list


def sgf_to_list(input_sgf_path, num_moves = 500):
    """ read sgf file to make list of moves up to num_moves """
    file_encoding = detect_encoding(input_sgf_path)
    if file_encoding == 'unknown':
        raise ValueError("Unknown encoding of file: " + input_sgf_path) 
    bw_position_list = []

    with codecs.open(input_sgf_path, 'r', file_encoding) as input_file:
        for line in input_file:
            # Get all matched strings (;B[xx] or ;W[xx] or ;B[] or ;W[])
            bw_position_regex = r';[BW]\[[a-zA-Z]{0,2}\]' # 0 represents pass
            bw_position = re.findall(bw_position_regex, line)
            bw_position_list.extend(bw_position)

            if len(bw_position_list) > num_moves:
                break

    num_moves = min(num_moves, len(bw_position_list))
    return bw_position_list[:num_moves]


def convert_lower(moves):
    """ Convert moves list to lower (ex. ;B[PD] -> ;B[pd]) """
    moves_lower = [m[:2] + m[2:].lower() for m in moves]
    return moves_lower


def detect_encoding(file_path):
    # Use the first encoding that does not cause errors
    encodings_to_try = ['utf-8', 'sjis', 'ascii']
    for encoding in encodings_to_try:
        try:
            with codecs.open(file_path, 'r', encoding=encoding) as file:
                file.read()
            return encoding
        except UnicodeDecodeError:
            continue

    # Return default encoding
    return 'unknown'



##### Read query sgf file and make queries #####

def read_query_sgf(input_sgf_path, num_moves = 500):
    """ Read query sgf file to make possible symmetric moves """
    moves = sgf_to_list(input_sgf_path, num_moves)
    moves_list = make_all_symmetries(moves)
    return moves_list



##### Generate possible symmetric moves #####

def make_all_symmetries(moves):
    """ Generate list of 16-type possible symmetric moves """
    moves_list = []
    
    # extract each coordinate
    BW_coords = list(map(extract_coords, moves))
    
    # exchange 1st and 2nd players
    WB_coords = exchange_BW(BW_coords)
    
    # generate possible moves
    moves_list.extend(make_symmetric_moves_list(BW_coords))
    moves_list.extend(make_symmetric_moves_list(WB_coords))
    return moves_list


def extract_coords(move):
    """ Extract coordinate from moves (ex. ';B[pd]' -> 'pd') """
    if len(move) != 6:
        return ""
    else:
        return move[3:5]


def make_moves(coords):
    """ Make moves from coodinates (ex. 'pd' -> ';B[pd]') """
    moves = [";B[" + coords[i] + "]" if (i % 2 == 0)
                  else ";W[" + coords[i] + "]"
                  for i in range(len(coords))]
    return(moves)


def reverse_position(coord):
    """ Reverse alphabet position (ex. a -> s, b -> r) """
    return chr(212 - ord(coord))


def exchange_BW(coords):
    """ Exchange coordinates of moves between 1st and 2nd players """
    l = len(coords)
    if l % 2 != 0:
        coords.append("tt") # "tt" means pass
    WB_coords = [coords[i + 1] if (i % 2 == 0) else coords[i - 1]
                 for i in range(l)]
    return WB_coords


def make_symmetric_moves_list(xy_coords):
    """
    8-type variations of moves generated from xy_coords
    via symmetric operation (rotation, mirror)
    """
    variations = [] # list of 8-type variations

    x_coords = [c[0] for c in xy_coords] # list of x coordinates
    y_coords = [c[1] for c in xy_coords] # list of y coordinates

    rev_x_coords = list(map(reverse_position, x_coords)) # (-X) 型
    rev_y_coords = list(map(reverse_position, y_coords)) # (-Y) 型
    
    x_group = [x_coords, rev_x_coords]
    y_group = [y_coords, rev_y_coords]
    
    for coord1 in x_group:
        for coord2 in y_group:
            temp = [c1 + c2 for c1, c2 in zip(coord1, coord2)] # XY 型
            variations.append(make_moves(temp))
            temp = [c2 + c1 for c1, c2 in zip(coord1, coord2)] # YX 型
            variations.append(make_moves(temp))

    return(variations)



##### Calculate similarity to every sgf of database

def custom_LS(s1, s2, *, score_cutoff = None):
    """
    Levenshtein similarity with customized weight
    Return normalized score between 0 and 100
    """
    score = Levenshtein.normalized_similarity(s1, s2, weights = (3, 1, 3))
    if (score_cutoff is not None) and score < score_cutoff:
        return None
    return 100 * score

def calc_similarity(query, database):
    """
    Calculate similarity of possible moves in list-type query
    Choose highest similarity in possible moves
    Return list-type similarity
    """
    num_database = len(database)
    similarity = [0 for i in range(num_database)] # default = minimum value

    for moves in query:
        # calculate similarity to every sgf of database
        temp = process.extract(moves, database, limit = num_database, 
                               scorer = custom_LS)
        # re-sort temp by database index
        temp = sorted(temp, key = lambda x: x[2])
        for i in range(num_database):
            if temp[i][1] > similarity[i]:
                similarity[i] = temp[i][1]
    
    return similarity


if __name__ == "__main__":
    main()