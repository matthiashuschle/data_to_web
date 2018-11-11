import os
import re
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from bokeh.embed import components
from bokeh.resources import CDN, INLINE
from bokeh.io import curdoc
from bokeh.document import Document
from . import templates


class CompositePage:

    class PageElement:

        def __init__(self, index, title=None, caption=None, plot_object=None, name=None, format_fcn=None):
            self.ix = index
            self.title = title
            self.caption = caption
            self.plot_object = plot_object  # used externally to create html
            self.name = name
            self._html = None
            self.format_fcn = format_fcn
            if name is not None:
                if len(name) != len(re.sub(r'[^0-9A-Za-z_]+', '', name)):
                    raise ValueError('invalid name.')

        @property
        def html(self):
            return templates.TPL_H2_CAPTION_OBJECT.render(
                title=self.title,
                caption=self.caption,
                object=self._html
            )

        @property
        def html_raw(self):
            return self._html

        @html.setter
        def html(self, val):
            self._html = val

    def __init__(self, title=None, caption=None, bokeh_resources_inline=False):
        """ This class helps creating HTML-Dashboards containing tables and plots.

        :param str title: title of the output page
        :param str caption: description of the page
        """
        self.title = title
        self.caption = caption
        self._tables = []
        self._bokeh_figs = []
        self._plt_figs = []
        self._index = 0
        self._bokeh_resources = INLINE if bokeh_resources_inline else CDN
        self._scrollable_tables = False

    @property
    def index(self):
        """ auto-increment to maintain order of objects

        :return: index
        :rtype: int
        """
        self._index += 1
        return self._index

    def add_table(self, df, title=None, caption=None, int_convert=True,
                  non_scientific=True, html=None, format_fcn=None):
        """ Add a DataFrame as table.

        :param pd.DataFrame df: dataframe to be transformed into a table
        :param str title: title of the object
        :param str caption: description of the object
        :param bool int_convert: try to convert numeric columns losslessly to int
        :param bool non_scientific: suppress scientific number format for floats
        :param str html: HTML to display instead of auto-generated from DataFrame
        :param callable format_fcn: function that modifies an excel row
        :return: None
        """
        element_table = self.PageElement(self.index, title=title, caption=caption,
                                              plot_object=df.copy(), format_fcn=format_fcn)
        if html is None:
            formatted_html = self.df_to_html(df, int_convert=int_convert, non_scientific=non_scientific)
            element_table.html = formatted_html
        else:
            element_table.html = html
        self._tables.append(element_table)

    def add_table_from_fields(self, fields, title=None, caption=None):
        """ Add a DataFrame as table.

        :param TableFieldArray fields: field definition
        :param str title: title of the object
        :param str caption: description of the object
        :return: None
        """
        element_table = self.PageElement(self.index, title=title, caption=caption,
                                              plot_object=fields.df_pretty.copy())
        self._tables.append(element_table)

    def add_bokeh_figure(self, fig, title=None, caption=None):
        """ Add a bokeh figure to the page as JavaScript

        :param bokeh.plotting.figure.Figure fig: figure
        :param str title: title of the object
        :param str caption: description of the object
        :return: None
        """
        element_bokeh = self.PageElement(self.index, title=title, caption=caption,
                                              plot_object=fig)
        self._bokeh_figs.append(element_bokeh)

    def add_plt(self, axes=None, title=None, caption=None, **kwargs):
        """ Add a matplotlib plot.

        :param plt.Axes axes: plot object
        :param str title: title of the object
        :param str caption: description of the object
        :param dict kwargs: keyword arguments for the bitmap transformation. See :meth:`plt.savefig`
        :return: None
        """
        if axes:
            if not hasattr(axes, 'number'):
                axes = axes.get_figure()
        element_plt = self.PageElement(self.index, title=title, caption=caption)
        element_plt.html = self.plt_to_html(axes=axes, **kwargs)
        self._plt_figs.append(element_plt)

    @property
    def pagecontent(self):
        return [x for x in sorted(self._tables + self._bokeh_figs + self._plt_figs, key=lambda x: x.ix)]

    @property
    def html(self):
        """ prepares HTML output, includes creation of bokeh JS code. """
        header_elements = []
        # process bokeh and set HTML
        if len(self._bokeh_figs):
            header_elements.extend(self._process_bokeh())
        # process tables
        page = templates.TPL_BOOTSTRAP_PAGE_BASE.render(
            title=self.title,
            header_elements=header_elements,
            body_content=templates.TPL_BOOTSTRAP_CONTAINER.render(
                content='\n'.join([
                    templates.TPL_H1_CAPTION.render(page_title=self.title, caption=self.caption),
                    templates.TPL_COMPOSITE_PAGE.render(pagecontent=self.pagecontent)
                ])
            ),
        )
        return page

    def _process_bokeh(self):
        """ Add header elements for bokeh plots and create bokeh server entries if necessary. """
        header_elements = [self._bokeh_resources.render_js(), self._bokeh_resources.render_css()]
        bokeh_script, bokeh_divs = components([x.plot_object for x in self._bokeh_figs])
        for idiv, bokeh_div in enumerate(bokeh_divs):
            self._bokeh_figs[idiv].html = bokeh_div
        header_elements.append(bokeh_script)
        return header_elements

    @staticmethod
    def _non_scientific_float_format(number):
        if number == 0:
            return '0.0'
        if abs(number) >= 10 ** 10:
            return '%.05e' % number
        if abs(number) >= 10 ** 6:
            return '%.2f' % number
        if abs(number) >= 1:
            return '%.04f' % number
        if abs(number) >= 10 ** -3:
            return '%.06f' % number
        return '%.05e' % number

    @classmethod
    def df_to_html(cls, df, int_convert=True, non_scientific=True):
        """ convert a dataframe to a HTML table.

        :param pd.DataFrame df: dataframe
        :param bool int_convert: try to convert numeric columns losslessly to int
        :param bool non_scientific: suppress scientific number format for floats
        :return: HTML string
        :rtype: str
        """
        if int_convert:
            df = cls._convert_int_columns(df)
        old_width = pd.get_option('display.max_colwidth')
        pd.set_option('display.max_colwidth', -1)
        old_float_format = pd.get_option('display.float_format')
        if non_scientific:
            pd.set_option('display.float_format', cls._non_scientific_float_format)
        try:
            output = df.to_html(classes=['table', 'table-striped', 'table-bordered'])
        finally:
            pd.set_option('display.max_colwidth', old_width)
            pd.set_option('display.float_format', old_float_format)
        return output

    @staticmethod
    def _convert_int_columns(df):
        """ Convert integer columns where it is possible without information loss.

        :param pd.DataFrame df: dataframe
        :return: DataFrame with replaced columns
        """
        df = df.copy()
        assert isinstance(df, pd.DataFrame)
        for col in df.columns[:]:
            if df[col].dtype != np.float:
                continue
            try:
                newcol = df[col].astype(int)
            except ValueError:
                continue
            # noinspection PyTypeChecker
            if not np.all(newcol == df[col]):
                continue
            df[col] = newcol
        return df

    @staticmethod
    def plt_to_html(axes=None, **kwargs):
        """ convert a pyplot object to HTML.

        :param plt.axes axes: figure
        :param dict kwargs: conversion args. See :meth:`plt.savefig`
        :return: HTML string
        :rtype: str
        """
        output = io.BytesIO()
        if axes:
            plt.figure(axes.number)
        if 'dpi' not in kwargs:
            kwargs['dpi'] = 75
        plt.savefig(output, **kwargs)
        data_uri = base64.b64encode(output.getbuffer()).decode('utf-8').replace('\n', '')
        return '<div><img src="data:image/png;base64,%s" /></div>' % data_uri

    @property
    def bokeh_json_string(self):
        """ Get a json string only for used bokeh figures. """
        t_doc = Document(title=curdoc().title)
        for element in self._bokeh_figs:
            t_doc.add_root(element.plot_obj)
        return t_doc.to_json_string()

    def publish(self, name=None, overwrite=False):
        """ invoke creation of an HTML file with self.html as content.

        :param str name: override name for output file
        :param bool overwrite: allow overwriting existing files
        :return: path of output file
        :rtype: str
        """
        name = name or self.title
        name = self.extract_name(name)
        if name is None or not len(name):
            raise ValueError('invalid basename for output file: %s.html' % name)
        filepath = os.path.abspath(name + '.html')
        url = 'file:///' + filepath
        if os.path.exists(filepath) and not overwrite:
            raise OSError('file exists: %s' % filepath)
        with open(filepath, 'w') as fout:
            fout.write(self.html)
        if url is not None:
            print('access output via:', url)
        return filepath

    @staticmethod
    def extract_name(name):
        """ create a valid name without whitespaces """
        name = name.replace(' ', '_')
        name = re.sub(r'[^0-9A-Za-z\-_.]+', '', name)
        return name
