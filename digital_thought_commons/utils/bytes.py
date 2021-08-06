KB = float(1000)
MB = float(KB ** 2)  # 1,048,576
GB = float(KB ** 3)  # 1,073,741,824
TB = float(KB ** 4)  # 1,099,511,627,776


def bytes_to_readable_unit(size_bytes: int):
    size_bytes = float(size_bytes)

    if size_bytes < KB:
        return '{0} {1}'.format(size_bytes, 'Bytes' if 0 == size_bytes > 1 else 'Byte')
    elif KB <= size_bytes < MB:
        return '{0:.2f} KB'.format(size_bytes / KB)
    elif MB <= size_bytes < GB:
        return '{0:.2f} MB'.format(size_bytes / MB)
    elif GB <= size_bytes < TB:
        return '{0:.2f} GB'.format(size_bytes / GB)
    elif TB <= size_bytes:
        return '{0:.2f} TB'.format(size_bytes / TB)


class ByteSize:

    def __init__(self, size_bytes: int) -> None:
        self.size_bytes = size_bytes

    def __str__(self) -> str:
        return bytes_to_readable_unit(self.size_bytes)

    @classmethod
    def build(cls, size_bytes: int):
        return cls(size_bytes)

    @classmethod
    def build_from_str_with_unit(cls, size_: str):
        if 'kB' in size_:
            return cls(int(float(size_.replace('kB', '').strip()) * KB))
        elif 'KB' in size_:
            return cls(int(float(size_.replace('KB', '').strip()) * KB))
        elif 'MB' in size_:
            return cls(int(float(size_.replace('MB', '').strip()) * MB))
        elif 'GB' in size_:
            return cls(int(float(size_.replace('GB', '').strip()) * GB))
        elif 'GB' in size_:
            return cls(int(float(size_.replace('TB', '').strip()) * TB))
        elif 'B' in size_:
            return cls(int(float(size_.replace('B', '').strip())))

        raise Exception(f'Unable to interpret unit in value: {size_}')

    def as_bytes(self):
        return self.size_bytes

    def as_kilobytes(self):
        return self.size_bytes / KB

    def as_megabytes(self):
        return self.size_bytes / MB

    def as_gigabytes(self):
        return self.size_bytes / GB

    def as_terabytes(self):
        return self.size_bytes / TB

    def pretty(self):
        return bytes_to_readable_unit(self.size_bytes)
