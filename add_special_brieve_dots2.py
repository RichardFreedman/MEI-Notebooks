import bs4
import optparse
import sys

import intervals
from intervals import *
from intervals import main_objs

def parse_args(description):
    parser = optparse.OptionParser(description=description)
    parser.add_option("-i", "--input_filename", type="string", \
        help="input the faulty mei with inconsistent measure offsets accross voices")
    parser.add_option("-o", "--output_filename", type="string", \
        help="output the corrected mei file")

    mandatories = ["input_filename", "output_filename"]
    (opts, args) = parser.parse_args()
    for m in mandatories:
        if not opts.__dict__[m]:
            parser.print_help()
            sys.exit()
    return opts

def has_diff_measure_offsets(model):
    # get columns
    measures = model.getMeasure()
    # compare each columns, return FALSE for strange columns
    voices = measures.columns
    first_voice = measures[voices[0]]

    for voice in voices[1:]:
        if not first_voice.equals(measures[voice]):
            return True
    return False

def find_three_to_one_8_rests(model):
    ms = model.getMeasure()
    num_voices = len(ms.columns)

    # create a df with time signature and note_rests
    ts = model.getTimeSignature()
    nr = model.getNoteRest()
    dur = model.getDuration(nr)

    # combine and divide dataframe
    big_df = pd.concat([nr, ts, dur, ms], axis=1)
    nr_part = big_df.iloc[:, :num_voices]
    ts_part = big_df.iloc[:, num_voices:num_voices * 2]
    dur_part = big_df.iloc[:, num_voices * 2:num_voices * 3]
    ms_part = big_df.iloc[:, num_voices * 3:]
    ts_part.fillna(method='ffill', axis=0, inplace=True)

    # conditions
    ts_condition = ts_part == '3/1'
    nr_condition = nr_part == 'Rest'
    dur_condition = dur_part == 8.0

    ms_part = ms_part[ts_condition & nr_condition & dur_condition].dropna(how='all')

    return ms_part

def identify_faulty_measures_offsets():
    files = FILES_MEASURES_FIXED
    models = build_crim_models(files)

    for file, model in models.items():
        print(file)
        if has_diff_measure_offsets(model):
            print("False")
            print(find_three_to_one_8_rests(model))
        else:
            print("True")

def _get_prettified(tag, curr_indent, indent):
    out = ''
    for x in tag.find_all(recursive=False):
        if len(x.find_all()) == 0 and x.string:
            content = x.string.strip(' \n')
        else:
            content = '\n' + _get_prettified(x, curr_indent + ' ' * indent, indent) + curr_indent

        attrs = ' '.join([f'{k}="{v}"' for k, v in x.attrs.items()])
        out += curr_indent + (
            '<%s %s>' % (x.name, attrs) if len(attrs) > 0 else '<%s>' % x.name) + content + '</%s>\n' % x.name

    return out


def get_prettified(tag, indent):
    """
    Output the source into the correct mei XML format
    """
    return _get_prettified(tag, '', indent)

def add_dots(incorrect_file, measures_df, output):

    correct_output = open(output, "w+")
    with open(incorrect_file, 'r') as incorrect_input:
        data = incorrect_input.read()

    incorrect_data = bs4.BeautifulSoup(data, "xml")

    # in each voice, find measure with specific numbers
    measures_df = measures_df.dropna(how='all')
    measures_df = measures_df.stack()
    for measure_num in measures_df:
        # find the corresponding voice and measure
        measure = incorrect_data.find("measure", {"n":str(int(measure_num))})
        # get their mRest tag
        if measure:
            mRests = measure.find_all("mRest")
            for mRest in mRests:
                if mRest.has_attr('dots'):
                    continue
                else:
                    mRest['dots']='1'
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + get_prettified(incorrect_data, indent=2)
    correct_output.write(out)
    correct_output.close()

def main():

    args = parse_args("Arguments for correcting a MEI file.")
    model = CorpusBase([args.input_filename]).scores[0]

    if has_diff_measure_offsets(model):
        print(args.input_filename + " has inconsistent measure offsets across voices.")
        measures_df = find_three_to_one_8_rests(model)
        add_dots(args.input_filename, measures_df, args.output_filename)
        print('File fixed by adding a dots="1" to the 3/1, 8.0 duration breives')

        fixed_model = CorpusBase([args.output_filename]).scores[0]
        if has_diff_measure_offsets(fixed_model):
            print("FIX FAILED: Please find another way to address this problem.")
        else:
            print("FIX SUCCEEDED: Corrected file is available at " + args.output_filename)
    else:
        print("File has consistent measures offsets across voices, no fixing necessary.")

# def test():
#     input_file = 'https://raw.githubusercontent.com/CRIM-Project/CRIM-online/master/crim/static/mei/MEI_3.0/CRIM_Mass_0021_4.mei'
#     output_file = 'cleaned_mei/CRIM_Mass_0021_4.mei'
#     model = CorpusBase([input_file]).scores[0]
#     measures_df = find_three_to_one_8_rests(model)
#     add_dots('incorrect_mei/CRIM_Mass_0021_4.mei', measures_df, output_file)

main()
# test()
