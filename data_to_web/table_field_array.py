""" Provides Utility to convert DataFrames to HTML via Flask, JS, ...

Instantiate TableFieldArray with a list of ad-hoc TableField instances.
"""
from . import templates


class TableField:

    def __init__(self, name, is_data=True, visible=True, fcn=None, header=None, attributes_fcn=None):
        """ Handle juggling of Data columns by defining if they will be visible in the output or are input.

        Later in TableFieldArray, the data must contain all columns that are set as "is_data".
        "visible" is a shortcut to display an "is_data" field, even if formatting functions etc. apply.
        There is no reason whatsoever to include a field that is neither data nor visible.

        :param str name: column name in the input/output
        :param bool is_data: column is used in the input - if not, it is generated only for the output.
        :param bool visible: column is shown in the output - if not, it can still be used by any output column
        :param callable fcn: function to create output from input row.
            acts on itertuples, i.e. access columns as attribute, not by key
        :param str header: optional header to display in the output
        :param callable attributes_fcn: function to create attribute dictionary
        """
        self.name = name
        self.is_data = is_data
        self.visible = visible
        self.fcn = fcn
        self._header = header
        self._attributes_fcn = attributes_fcn

    @property
    def header(self):
        """
        :rtype: str
        """
        if self._header is None:
            return self.name
        return self._header

    @header.setter
    def header(self, value):
        self._header = value

    @property
    def has_header(self):
        """
        :rtype: bool
        """
        return self._header is not None

    @property
    def function(self):
        """
        :rtype: callable
        """
        if self.fcn is None:
            return lambda x: str(getattr(x, self.name))
        return self.fcn

    @property
    def attributes_fcn(self):
        if self._attributes_fcn is None:
            return lambda x: {}
        return self._attributes_fcn

    @staticmethod
    def format_int(val, none_to_zero=True):
        """ Format something to integer.

        :param val: value to format
        :param bool none_to_zero: convert None to 0. Raise otherwise.
        :return: int as string
        :rtype: str
        """
        if val is None:
            if none_to_zero:
                return 0
            else:
                return 'None'
        return '%i' % int(float(val))

    @staticmethod
    def format_euro(val):
        """ Convert something to Euro amount.

        :param val: value to format
        :return: float as "x.xx €"
        """
        return '%.02f €' % float(val)

    @staticmethod
    def format_percent(val, precision=1):
        """ Convert something to percentage. 0.5 -> 50.00 %

        :param val: value to format
        :param int precision: number of decimals
        :return: float as percentage x.xx %
        """
        return ('%%.0%if %%%%' % precision) % (float(val) * 100.)

    @classmethod
    def format_factory(cls, format_type, field_name, **kwargs):
        """ Creates functions for formatting. Needed as named attributes might be accessed and depend on scope.

        :param str format_type: "int", "euro", or "percent"
        :param str field_name: column name of value to format
        :param kwargs: additional arguments for format function
        :return: format function
        :rtype: callable
        """
        if format_type == 'int':
            return lambda x: cls.format_int(getattr(x, field_name), **kwargs)
        elif format_type == 'euro':
            return lambda x: cls.format_euro(getattr(x, field_name))
        elif format_type == 'percent':
            return lambda x: cls.format_percent(getattr(x, field_name), **kwargs)


class TableFieldArray:

    def __init__(self, table_fields=None, data=None):
        """ Manages the conversion from DataFrame to web.

        Assuming you don't generate HTML directly, but use a dictionary like object to
        generate it via JS or Flask. just give it the array of TableField instances and the data,
        and the table_dict property provides your data:
        {
            "thead": {"v": [head1, head2, ...]},
            "tbody": [{
                "v": [row_1_val_1, row1_val2, ...],
                "a": [{row1_attr1_key: row1_attr1_val, ...}, ...]
            }, ...]
        }

        The df_pretty property provides the data with column names and order aligned with TableFields.
        (intended for download option)

        :param table_fields:
        :param data:
        """
        self._table_fields = table_fields or []
        self._data = data
        self._table_dict = None
        self._table_html = None
        self._df_pretty = None

    def _reset_properties(self):
        """ Clear cache. """
        self._table_dict = None
        self._df_pretty = None

    @property
    def table_fields(self):
        """ list of TableField instances.

        :rtype: list
        """
        return self._table_fields

    @table_fields.setter
    def table_fields(self, val):
        """ Setter for table_fields

        :param list val: new table_fields
        """
        self._reset_properties()
        self._table_fields = val

    @property
    def data(self):
        """ DataFrame containing the raw data.

        :rtype: pd.DataFrame
        """
        return self._data

    @data.setter
    def data(self, val):
        """ setter for data.

        :param pd.DataFrame val: new raw data
        """
        self._reset_properties()
        self._data = val

    def __iter__(self):
        return self.table_fields.__iter__()

    def get_field(self, name):
        """ Retrieve the TableField instance with the given name.

        :param str name: name property of desired TableField
        :rtype: TableField
        """
        for field in self.table_fields:
            if field.name == name:
                return field
        raise KeyError('Field %r not found.' % name)

    def __getitem__(self, item):
        return self.get_field(item)

    def _filter_data(self):
        return [x for x in self.table_fields if x.is_data]

    def _filter_visible(self):
        return [x for x in self.table_fields if x.visible]

    def get_data_fields(self):
        return [x.name for x in self._filter_data()]

    def get_data_header(self):
        return [x.header for x in self._filter_data()]

    def get_output_header(self):
        return [x.header for x in self._filter_visible()]

    def get_output_functions(self):
        return [x.function for x in self._filter_visible()]

    def get_output_tag_attribute_functions(self):
        return [x.attributes_fcn for x in self._filter_visible()]

    def get_column_formatters(self):
        return [x for x in zip(self.get_output_functions(), self.get_output_tag_attribute_functions())]

    def iter_formatted_rows(self):
        """ Apply formatters: string and attributes.

        returns a tuple (formatted values, attributes) per data row.

        :rtype: tuple
        """
        formatters = self.get_column_formatters()
        for row in self.iter_data_rows():
            vals = []
            attrs = []
            for fcn, attr_function in formatters:
                vals.append(fcn(row))
                attrs.append(attr_function(row))
            yield vals, attrs

    def iter_data_rows(self):
        """ Iterate row-tuples of the data content.

        :rtye: generator
        """
        data_cols = self.get_data_fields()
        if self.data is None:
            return []
        return (row for row in self.data[data_cols].itertuples())

    @property
    def table_dict(self):
        """ Return the output table as nested dict.

        :rtype: dict
        """
        if self._table_dict is None:
            self._table_dict = {
                'thead': {'v': self.get_output_header()},
                'tbody': [{'v': vals, 'a': attrs} for vals, attrs in self.iter_formatted_rows()]
            }
        return self._table_dict

    @property
    def table_html(self):
        if self._table_html is None:
            self._table_html = templates.TPL_TABLE.render(
                head=self.table_dict['thead']['v'], body=self.table_dict['tbody']
            )
        return self._table_html

    @property
    def df_pretty(self):
        """ Return a DataFrame with renamed columns.

        :rtype: pd.DataFrame
        """
        if self._df_pretty is None:
            data_fields = self.get_data_fields()
            data_headers = self.get_data_header()
            rename = {}
            for data_header, data_field in zip(data_headers, data_fields):
                if not isinstance(data_header, str):
                    data_header = data_header.string
                rename[data_field] = data_header
            self._df_pretty = self.data[data_fields].rename(columns=rename)
        return self._df_pretty
