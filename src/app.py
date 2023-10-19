from flask import Flask, request, render_template_string, redirect, url_for, render_template
from flask_ngrok import run_with_ngrok
import spacy
from spacy import displacy
import numpy as np
import pandas as pd
from markupsafe import Markup
import csv

app = Flask(__name__)

nlp = spacy.load('en_core_web_lg')

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Institutional Grammar</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        
        h1 {
            background-color: #333;
            color: #fff;
            text-align: center;
            padding: 20px 0;
            margin: 0;
        }
        
        form {
            max-width: 600px;
            margin: 0 auto;
            margin-top: 100px;
            padding: 20px;
            background-color: #fff;
            border: 1px solid #ddd;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        
        label {
            font-weight: bold;
        }
        
        textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            margin-bottom: 10px;
            resize: vertical;
        }
        
        input[type="submit"] {
            background-color: #333;
            color: #fff;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
        }
        
        input[type="submit"]:hover {
            background-color: #555;
        }
        
        h2 {
            margin-top: 20px;
            margin-left: 100px;
        }
        
        .output {
            border: 1px solid #ddd;
            padding: 10px;
            margin-right: 100px; 
            margin-left: 100px; 
        }
        .info{
            border: 1px solid #ddd;
            padding: 10px;
            margin-right: 100px; 
            margin-left: 100px; 
        }
    </style>
</head>
<body>
    <h1>Institutional Grammar</h1>
    <form method="POST" action="/">
        <label for="input_text">Enter Text:</label><br>
        <textarea name="input_text" rows="4" cols="50"></textarea><br><br>
        <input type="submit" value="Process">
    </form>
    {% if output_text %}
        <h2>Processed Text:</h2>
        <p class="output">{{ output_text }}</p>
        <div class="info">
            <p><span style="background-color: cyan;">Attribute</span></p>
            <p><span style="background-color: yellow;">Aim</span></p>
            <p><span style="background-color: lightpink;">Deontic</span></p>
        </div>
        <form method="POST" action="/feedback">
            input type="hidden" name="attr_gen" value="{{ sentence }}">
            <input type="hidden" name="attr_gen" value="{{ attr_gen }}">
            <input type="hidden" name="aim_gen" value="{{ aim_gen }}">
            <input type="hidden" name="deontic_gen" value="{{ deontic_gen }}">
            <label for="attribute_feedback">Attribute Feedback:</label><br>
            <input type="text" name="attribute_feedback"><br><br>
            
            <label for="aim_feedback">Aim Feedback:</label><br>
            <input type="text" name="aim_feedback"><br><br>
            
            <label for="deontic_feedback">Deontic Feedback:</label><br>
            <input type="text" name="deontic_feedback"><br><br>
            
            <input type="submit" value="Submit Feedback">
        </form>
    {% endif %}
</body>
</html>
"""



@app.route('/', methods=['GET', 'POST'])
def text_processor():
    output_text = ""
    attr_gen = ""  # Initialize attr_gen, aim_gen, and deontic_gen as empty strings
    aim_gen = ""
    deontic_gen = ""
    
    if request.method == 'POST':
        input_text = request.form['input_text']
        # Process the input text (replace with your custom processing logic)
        # For now, just capitalize it as an example
        # output_text = input_text.upper()
        doc = nlp(input_text)
        doc = merge_phrases(doc)
        doc = merge_punct(doc)
        case, root_verb, root_aux = find_case(doc)
        aim_token, attr_token, deontic_token = tokenise(case, doc, root_verb, root_aux)
        highlighted_text = input_text  # Start with a copy of the input text
        if aim_token:
            for token in aim_token:
                highlighted_text = highlighted_text.replace(token.text, f'<span style="background-color: yellow;">{token.text}</span>')
        if attr_token:
            for token in attr_token:
                highlighted_text = highlighted_text.replace(token.text, f'<span style="background-color: cyan;">{token.text}</span>')
        if deontic_token:
            for token in deontic_token:
                highlighted_text = highlighted_text.replace(token.text, f'<span style="background-color: lightpink;">{token.text}</span>')

        # Convert spaCy tokens to strings or extract text content
        attr_gen = " ".join([token.text for token in attr_token])
        aim_gen = " ".join([token.text for token in aim_token])
        deontic_gen = " ".join([token.text for token in deontic_token])
        sentence = input_text
        # Set the output text to the highlighted input text
        print(highlighted_text)
        output_text = Markup(highlighted_text)
    
    return render_template_string(
        html_template,
        output_text=output_text,
        attr_gen=attr_gen,  
        aim_gen=aim_gen,
        deontic_gen=deontic_gen
    )


@app.route('/feedback', methods=['POST'])
def feedback():
    if request.method == 'POST':
        sentence = request.form.get('sentence')
        attribute_feedback = request.form.get('attribute_feedback')
        aim_feedback = request.form.get('aim_feedback')
        deontic_feedback = request.form.get('deontic_feedback')
        
        # Retrieve the generated values from hidden input fields
        sentence = request.form.get('sentence')
        attr_gen = request.form.get('attr_gen')
        aim_gen = request.form.get('aim_gen')
        deontic_gen = request.form.get('deontic_gen')

        # Append the feedback data to the CSV file
        with open('feedback.csv', mode='a', newline='') as csv_file:
            fieldnames = ['sentence', 'attr_gen', 'aim_gen', 'deontic_gen', 'attribute_feedback', 'aim_feedback', 'deontic_feedback']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            # Write the feedback data
            csv_writer.writerow({
                'sentence': sentence,
                'attr_gen': attr_gen,
                'aim_gen': aim_gen,
                'deontic_gen': deontic_gen,
                'attribute_feedback': attribute_feedback,
                'aim_feedback': aim_feedback,
                'deontic_feedback': deontic_feedback,
            })

        return redirect(request.referrer)


def find_case(doc):
    root_tokens = []
    for token in doc:
        ancestors = [t.text for t in token.ancestors]
        ancestors_token = [t for t in token.ancestors]
        children = [t.text for t in token.children]
        children_token = [t for t in token.children]
        left = [t.text for t in token.lefts]
        right = [t.text for t in token.rights]
        if(token.dep_ == "ROOT"):
            root_tokens.append(token)
    #         print(token.text, "\t", 
    #           token.pos_, "\t" )
    #         print("\n")
    #     print(token.text, token.pos_, token.dep_,ancestors,children)
    root_verb = []
    root_aux = []
    root_noun = []
    root_others = []
    case = 3

    for token in root_tokens:
        if(token.pos_ == 'VERB'):
            root_verb.append(token)
        elif(token.pos_ == 'AUX'):
            root_aux.append(token)
        elif(token.pos_ == 'NOUN'):
            root_noun.append(token)
        else:
            root_others.append(token)

    if(len(root_verb)>0):
        case = 1
    elif(len(root_aux)>0):
        case = 2
    elif(len(root_noun)>0):
        case = 3
    elif(len(root_others)>0):
        case = 3
    print(f"\n Case = {case}")
    return case, root_verb,root_aux

def merge_phrases(doc):
    with doc.retokenize() as retokenizer:
        for np in list(doc.noun_chunks):
            attrs = {
                "tag": np.root.tag_,
                "lemma": np.root.lemma_,
                "ent_type": np.root.ent_type_,
            }
            retokenizer.merge(np, attrs=attrs)
    return doc

def merge_punct(doc):
    spans = []
    for word in doc[:-1]:
        if word.is_punct or not word.nbor(1).is_punct:
            continue
        start = word.i
        end = word.i + 1
        while end < len(doc) and doc[end].is_punct:
            end += 1
        span = doc[start:end]
        spans.append((span, word.tag_, word.lemma_, word.ent_type_))
    with doc.retokenize() as retokenizer:
        for span, tag, lemma, ent_type in spans:
            attrs = {"tag": tag, "lemma": lemma, "ent_type": ent_type}
            retokenizer.merge(span, attrs=attrs)
    return doc

def tokenise(case,doc,root_verb,root_aux):
    
    aim_token = []
    attr_token = []
    deontic_token = []
    
    
    keywords = ["shall","may","must"]
    secondary_keywords = ["is","has","have","was","having"]
    
    
    if(case==1):
        #AIM
        #working on root_verb
        flag = 0
        #first adding all VERBS with conj and ccomp to the root_verb list
        for token in root_verb:
            for children in token.children:
                if(children.dep_ == 'ccomp' or children.dep_ == 'conj'):
                    root_verb.append(children)

        #in GIVEN ORDER in the list, if we find a token with both nsubj and aux then we return it
        for token in root_verb:
            children_dep = [child.dep_ for child in token.children]
            str1 = "nsubj"
            str2 = "aux"

            if(str1 in children_dep and str2 in children_dep):
                aim_token.append(token)
                flag = 1
                break #only 1 aim in this case
        #nusbjpass and aux if not aux and nsubj    
        #if we dont find any such VERB then we take entire root_verb as aim (some of them might be right as there could be multiple)
        if(flag == 0):
            aim_token = root_verb
        #NOTE: AIM never empty since CASE 1
        
        #DEONTIC
        #deontic won't be empty due to keywords and secondary keywords
        for token in aim_token:
            for child in token.children:
                if(child.dep_ =='aux' and child.pos_ == 'AUX'):
                    deontic_token.append(child)
                    break
            if(len(deontic_token)>0):
                break

        #if no such deontic found then search in keywords and later in secondary keywords
        if(len(deontic_token) == 0):
            for keyword in keywords:
                for token in doc:
                    if(keyword in token.text and token.pos_ =="AUX"):
                        deontic_token.append(token)
                        break
                if(len(deontic_token)>0):
                    break

        if(len(deontic_token) == 0):
            for keyword in secondary_keywords:
                for token in doc:
                    if(keyword in token.text and token.pos_ =="AUX"):
                        deontic_token.append(token)
                        break
                if(len(deontic_token)>0):
                    break
                    
        #ATTRIBUTE
        #first check for nsubj
        for token in aim_token:
            for entity in token.children:
                if(entity.dep_ =='nsubj' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                    attr_token.append(entity)

        #else check for nsubpass
        if(len(attr_token) == 0):
            for token in aim_token:
                for entity in token.children:
                    if(entity.dep_ =='nsubjpass' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                        attr_token.append(entity)

        #else if empty then check in entire sentence
        if(len(attr_token) == 0):
            for token in doc:
                for entity in token.children:
                    if(entity.dep_ =='nsubj' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                        attr_token.append(entity)
                        break
                if(len(attr_token) > 0):
                    break

        if(len(attr_token) == 0):
            for token in doc:
                for entity in token.children:
                    if(entity.dep_ =='nsubjpass' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                        attr_token.append(entity)
                        break
                if(len(attr_token) > 0):
                    break
                    
                    
                    
    elif(case==2):
        #AIM
        for token in root_aux:
            for children in token.children:
                if((children.dep_ == 'ccomp' or children.dep_ == 'conj') and children.pos_ == 'VERB'):
                    aim_token.append(children)

        if(len(aim_token) == 0):
            for children in token.children:
                if((children.dep_ == 'advcl') and children.pos_ == 'NOUN'):
                    aim_token.append(children)
            for token in aim_token:
                for children in token.children:
                    if((children.dep_ == 'ccomp' or children.dep_ == 'conj') and children.pos_ == 'VERB'):
                        aim_token.append(children)
                        
        if(len(aim_token) == 0):
            for token in root_aux:
                for children in token.children:
                    if(children.pos_ == 'VERB'):
                        aim_token.append(children)
        
        
            
        #DEONTIC
        #for deontic first check aux from root_aux else check from aim else from keywords and secondary keywords
        for token in root_aux:
            for children in token.children:
                if((children.dep_ == 'aux') and children.pos_ == 'AUX'):
                    deontic_token.append(children)
                    break
            if(len(deontic_token) > 0):
                break

        if(len(deontic_token) == 0):
            for token in aim_token:
                for child in token.children:
                    if(child.dep_ =='aux' and child.pos_ == 'AUX'):
                        deontic_token.append(child)
                        break
                if(len(deontic_token)>0):
                    break

        #if no such deontic found then search in keywords and later in secondary keywords
        if(len(deontic_token) == 0):
            for keyword in keywords:
                for token in doc:
                    if(keyword in token.text and token.pos_ =="AUX"):
                        deontic_token.append(token)
                        break
                if(len(deontic_token)>0):
                    break

        if(len(deontic_token) == 0):
            for keyword in secondary_keywords:
                for token in doc:
                    if(keyword in token.text and token.pos_ =="AUX"):
                        deontic_token.append(token)
                        break
                if(len(deontic_token)>0):
                    break
                    
        #ATTRIBUTE
        for token in root_aux:
            for entity in token.children:
                if(entity.dep_ =='nsubj' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                    attr_token.append(entity)

        for token in aim_token:
            for entity in token.children:
                if(entity.dep_ =='nsubj' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                    attr_token.append(entity)

        #else check for nsubpass
        if(len(attr_token) == 0):
            for token in aim_token:
                for entity in token.children:
                    if(entity.dep_ =='nsubjpass' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                        attr_token.append(entity)

        #else if empty then check in entire sentence
        if(len(attr_token) == 0):
            for token in doc:
                for entity in token.children:
                    if(entity.dep_ =='nsubj' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                        attr_token.append(entity)
                        break
                if(len(attr_token) > 0):
                    break

        if(len(attr_token) == 0):
            for token in doc:
                for entity in token.children:
                    if(entity.dep_ =='nsubjpass' and (entity.pos_ == "PROPN" or entity.pos_ == "NOUN" or entity.pos_ == "PRON")):
                        attr_token.append(entity)
                        break
                if(len(attr_token) > 0):
                    break
        
        if(len(aim_token) == 0):
            for token in attr_token:
                for children in token.children:
                    if(children.pos_ == 'VERB'):
                        aim_token.append(children)
                        break
                if(len(aim_token)>0):
                    break
                
    elif(case==3 or case==4):
        entity_set = []
        #trying to extract the most common case - a verb with nsubj AND aux both OR try heuristic1
        for token  in doc:
            if(token.pos_ == 'VERB'):
                child_dependency = [child.dep_ for child in token.children]
                str1 = "aux"
                str2 = "nsubj"
                if((str1 in child_dependency) and (str2 in child_dependency)):
                    req_token = []
                    req_token.append(token)
                    for dependencies in token.children:
                        if(dependencies.dep_ == 'aux'):
                            req_token.append(dependencies)
                            break
                    for dependencies in token.children:
                        if(dependencies.dep_ == 'nsubj'):
                            req_token.append(dependencies)
                            break
                    entity_set.append(req_token)
                    
        for token_pair in entity_set:
            for token in token_pair:
                if(token.pos_=='VERB'):
                    aim_token.append(token)
                if(token.dep_=='aux'):
                    attr_token.append(token)
                if(token.dep_=='nsubj'):
                    deontic_token.append(token)
                    
    return aim_token,attr_token,deontic_token


if __name__ == '__main__':
    app.run()
