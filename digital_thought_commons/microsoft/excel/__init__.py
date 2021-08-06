import logging
import pathlib

import xlsxwriter
import yaml


class Spreadsheet(xlsxwriter.Workbook):

    def __init__(self, filename=None, template=None):
        super().__init__(filename)
        if template is None:
            template = str(pathlib.Path(__file__).parent.absolute()) + '../../_resources/microsoft/excel/defaultExcel.yaml'

        try:
            with open(template, 'r') as _template:
                self.template_config = yaml.safe_load(_template)
            self.template = template
            logging.debug("Applying Template: {}".format(self.template))
            self._apply_template(self.template_config)
        except Exception as ex:
            logging.exception("Error [{}] Applying Template: {}".format(str(ex), self.template))

    def _add_formats(self, template_config):
        self.custom_formats = {}
        if 'formats' in template_config:
            for fmt in template_config['formats']:
                logging.debug("Creating Format {}".format(fmt['name']))
                self.custom_formats[fmt['name']] = self.add_format(fmt['settings'])

    def _apply_worksheet_formatting(self, wksheet, worksheet):
        if 'formattings' in wksheet:
            if 'columns' in wksheet['formattings']:
                for column_formatting in wksheet['formattings']['columns']:
                    logging.debug("Applying Column Format")
                    first = column_formatting['first']
                    last = column_formatting['last']
                    format_config = None
                    width = None
                    options = None
                    if 'format' in column_formatting:
                        format_config = self.custom_formats[column_formatting['format']]
                    if 'width' in column_formatting:
                        width = column_formatting['width']
                    if 'options' in column_formatting:
                        options = column_formatting['options']

                    worksheet.set_column(first_col=first, last_col=last, width=width, cell_format=format_config, options=options)

            if 'rows' in wksheet['formattings']:
                for row_formatting in wksheet['formattings']['rows']:
                    logging.debug("Applying Row Format")
                    row_number = row_formatting['row']
                    format_config = None
                    height = None
                    options = None
                    if 'format' in row_formatting:
                        format_config = self.custom_formats[row_formatting['format']]
                    if 'height' in row_formatting:
                        height = row_formatting['height']
                    if 'options' in row_formatting:
                        options = row_formatting['options']

                    worksheet.set_row(row=row_number, height=height, cell_format=format_config, options=options)

    def _apply_merges(self, merge_ranges, worksheet):
        for merge in merge_ranges:
            range = merge['range']
            value = None
            format = None

            if 'value' in merge:
                value = merge['value']

            if 'format' in merge:
                format = merge['format']

            worksheet.merge_range(range, cell_format=self.custom_formats[format], data=value)

    def _apply_preset_values(self, presets, worksheet):
        for preset in presets:
            row = preset['row']
            column = preset['column']
            value = preset['value']
            format = None

            if 'format' in preset:
                format = preset['format']

            if format:
                worksheet.write(row, column, value, self.custom_formats[format])
            else:
                worksheet.write(row, column, value)

    def _apply_template(self, template_config):
        self.name = template_config['name']
        self.description = template_config['description']

        self._add_formats(template_config)

        self.template_worksheets = {}
        if 'worksheets' in template_config:
            for wksheet in template_config['worksheets']:
                worksheet = self.add_worksheet(wksheet['label'])
                self.template_worksheets[wksheet['name']] = worksheet

                self._apply_worksheet_formatting(wksheet, worksheet)

                if 'freeze_pane' in wksheet:
                    logging.debug("Applying Freeze Panes")
                    worksheet.freeze_panes(col=wksheet['freeze_pane']['column'], row=wksheet['freeze_pane']['row'])

                if 'merge_ranges' in wksheet:
                    logging.debug("Applying Merge Ranges")
                    self._apply_merges(wksheet['merge_ranges'], worksheet)

                if 'preset_values' in wksheet:
                    logging.debug("Applying Preset Values")
                    self._apply_preset_values(wksheet['preset_values'], worksheet)
