from jinja2 import Template

# title, body_content, header_elements
TPL_BOOTSTRAP_PAGE_BASE = Template('''\
<!doctype html>
<html lang="en">
  <head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
    
    <!-- Bootstrap JS -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
    
    {% for header in header_elements %}{{header}}{% endfor %}

    <title>{{title}}</title>
  </head>
  <body>
    {{body_content}}
  </body>
</html>
''')

# content
TPL_BOOTSTRAP_CONTAINER = Template('''\
<div class="container">{{content}}</div>''')

# page_title(o), caption(o)
TPL_H1_CAPTION = Template('''\
{% if page_title is not none %}<h1>{{page_title}}</h1>{% endif %}
    {% if caption is not none %}<p>{{caption}}</p>{% endif %}
''')

# pagecontent
TPL_COMPOSITE_PAGE = Template('''\
    {% for element in pagecontent %}
        <div>
            {{element.html}}
        </div>
    {% endfor %}
''')

# title(o), caption(o), object
TPL_H2_CAPTION_OBJECT = Template('''\
        {% if title is not none %}<h2>{{title}}</h2>{% endif %}
        {% if caption is not none %}<p>{{caption}}</p>{% endif %}
        <div align="center">{{object}}</div>''')

# head(o), body(o)
TPL_TABLE = Template('''\
<table class="table table-striped table-bordered">
  {% if head %}
  <thead>
    <tr>
      {% for val in head %}<th>{{val}}</th>{% endfor %}
    </tr>
  </thead>
  {% endif %}
  {% if body %}
  <tbody>
    {% for row in body %}
    <tr>
      {% for val in row.v %}
      <td{% for attr_name, attr_val in row.a.items() %} {{attr_name}}="{{attr_val}}"{% endfor %}>{{val}}</td>
      {% endfor %}
    </tr>
    {% endfor %}
  </tbody>
  {% endif %}
</table>
''')
