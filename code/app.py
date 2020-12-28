import os
import fnmatch
import codecs
import pymongo
from pymongo.collection import ReturnDocument
import bson
from bson.binary import Binary
import re


number_abstracts = 0
root_directory = '../raw/'
normalized_discipline = 0
normalized_journal_without_number = ''
normalized_journal_without_dot = ''
normalized_journal = ''
abstract_title_file = ''


myclient = pymongo.MongoClient("mongodb://localhost:27017/?retryWrites=false")

mydb = myclient["BasicTextPipeline"]

mycol = mydb["pre_processamento"]

# listar as áreas do conhecimento
fields = [ f for f in os.listdir(root_directory) if os.path.isdir(os.path.join(root_directory,f)) ]


for field in fields:
    print(field)
    discipline_directory = '../raw/'+field
    disciplines = [f for f in os.listdir(discipline_directory) if os.path.isdir(os.path.join(discipline_directory, f))]

    for discipline in disciplines:
        print("           - "+discipline)
        journal_directory = discipline_directory + '/' + discipline
        journals = [f for f in os.listdir(journal_directory) if os.path.isdir(os.path.join(journal_directory, f))]

        for journal in journals:
            normalized_journal_without_number = ''.join(i for i in journal if not i.isdigit())
            normalized_journal_without_dot    = normalized_journal_without_number.replace('.','')
            normalized_journal = normalized_journal_without_dot.strip()

            print("                           -> " + normalized_journal)
            abstract_directory = journal_directory + '/' + journal
            abstracts = [f for f in os.listdir(abstract_directory) if os.path.isfile(os.path.join(abstract_directory, f))]

            for abstract in abstracts:
                abstract_title_file = abstract.replace('.txt', '')
                complete_directory = abstract_directory + '/' + abstract

                fi = open(complete_directory, 'rb')
                encoded_content = Binary(fi.read())

                print("                                                                      - DIRECTORY: " + complete_directory)
                txt = open(complete_directory, encoding="utf8")
                lines = [line.rstrip('\n') for line in txt]

                publication_date = ""
                publication_year = ""
                abstract_journal = ""
                author = ""
                doi = ""

                for l in lines:
                    l.replace("\ufeff", "")

                    if l.startswith("PD "):
                        publication_date = l.replace("PD ", "")
                        publication_date = publication_date.replace(" ", "-")
                        publication_date = publication_date.lower()

                    if l.startswith("PY "):
                        publication_year = l.replace("PY ", "")

                    if l.startswith("DI "):
                        doi = l.replace("DI ", "")

                    if l.startswith("SO "):
                        journal = l.replace("SO ", "")
                        abstract_journal += journal.replace(" ", "-").lower()

                    if l.startswith("AF "):
                        author_complete = l.replace("AF ", "")
                        author_last, sep, author_first_complete = author_complete.partition(', ')
                        author_last = author_last.replace(" ", "-").lower()

                        aux = 2  # this is two taking into consideration that an abreviated name is the first letter of the name plus a comma eg. D.
                        author_first_list = author_first_complete.split(" ")
                        if len(author_first_list) == 1 and len(author_first_list[0]) != aux:
                            autor_first = author_first_list[0]
                        else:

                            for author_name in author_first_list:
                                if len(author_name) > aux and len(author_name) != aux:
                                    autor_first = author_name
                                    break
                                else:
                                    autor_first = ""
                        autor_first = autor_first.lower()

                        # SEARCH FOR TITLE
                        r = re.search("TI ((.*?\n)+)SO", "\n".join(map(str, lines)))

                        if r:
                            abstract_title = r.group(1).strip().replace("\n", " ").replace("    ", " ") + "\n"

                # start assembling string
                string_file_name = str(publication_year)

                if publication_date != "":
                    string_file_name += "-"
                    string_file_name += str(publication_date)
                else:
                    string_file_name += "00"

                # separating Date and DOI putting the annotation name
                string_file_name += "_JA_"

                if doi != "":
                    string_file_name += doi
                else:
                    string_file_name += "00-0000_0000000000000000"

                # separating DOI and file source
                string_file_name += "_" + str(abstract_journal)

                # adding first author name
                string_file_name += "_"
                string_file_name += str(author_last)
                if autor_first != "":
                    string_file_name += "_"
                    string_file_name += str(autor_first)

                # slashes are underscores
                # dots are dashes
                string_file_name = string_file_name.replace("/", "_")
                string_file_name = string_file_name.replace(".", "-")
                string_file_name = string_file_name.replace("(", "")
                string_file_name = string_file_name.replace(")", "")
                string_file_name = string_file_name.replace(",", "")

                if '&' in string_file_name:
                    string_file_name = string_file_name.replace("&", "and")

                # if string_file_name in nameOfFiles:
                #     string_file_name += '2'


                print("                                              * " + abstract_title_file)

                print("                                                           INFORMACOES PARA ARMAZENAR:")
                print("                                                                      - AC: " + field)
                print("                                                                      - DI: " + discipline)
                print("                                                                      - PE: " + normalized_journal)
                print("                                                                      - TI: " + abstract_title_file)
                print("                                                                      - FILE: " + abstract)

                mydict = {"TitleFileRaw": abstract_title_file.strip(),
                          "TitleFileBTP": string_file_name.strip(),
                          "TitleAbstract": abstract_title.strip(),
                          "Source": "Clarivate Analytics Web of Science",
                          "PublicationDate": publication_date.strip(),
                          "PublicationYear": publication_year.strip(),
                          "DOI": doi.strip(),
                          "Field": field.strip(),
                          "Discipline": discipline.strip(),
                          "Journal": normalized_journal,
                          "File": encoded_content}

                x = mycol.insert_one(mydict)

                number_abstracts = number_abstracts + 1

print (number_abstracts)