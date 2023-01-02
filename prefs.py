def load_prefs(filename):
    params_finished={}
    with open(filename, "r") as file:
        for line in file.readlines():
            if len(line)>0:
                params=line.split("=")
                if len(params)==2:
                    params[1]=params[1].replace("\n","")
                    for a in range(0,len(params)):
                        if (params[a].startswith("\"") and params[a].endswith("\"")) or (params[a].startswith("'") and params[a].endswith("'")):
                            params[a]=params[a][1:-1]
                    if params[1].replace(".","").isnumeric():
                        if "." in params[1]:
                            params[1]=float(params[1])
                        else:
                            params[1]=int(params[1])
                params_finished.update({params[0]: params[1]})
    return params_finished