"""Dumbest possible reference. No bit tricks. No bytes module. Just division and
modulo on a 32-bit int. Slower, longer, but each line reads like fourth-grade math.
"""


def ip_to_int(s: str) -> int:
    a, b, c, d = s.split('.')
    return int(a) * (1 << 24) + int(b) * (1 << 16) + int(c) * (1 << 8) + int(d)


def int_to_ip(x: int) -> str:
    a = x // (1 << 24)
    b = (x // (1 << 16)) % (1 << 8)
    c = (x // (1 << 8)) % (1 << 8)
    d = x % (1 << 8)
    return f"{a}.{b}.{c}.{d}"


class IPV4Iterator:
    def __init__(self, ip_or_cidr, reverse=False, step=1):
        if step <= 0:
            raise ValueError("step must be positive")
        if '/' in ip_or_cidr:
            ip_str, prefix_str = ip_or_cidr.split('/')
            seed = ip_to_int(ip_str)
            prefix = int(prefix_str)
            block_size = 1 << (32 - prefix)
            network = (seed // block_size) * block_size
            self.min_ip = network
            self.max_ip = network + block_size - 1
            self.current = seed
        else:
            self.current = ip_to_int(ip_or_cidr)
            self.min_ip = 0
            self.max_ip = (1 << 32) - 1
        self.reverse = reverse
        self.step = step

    def __iter__(self):
        return self

    def __next__(self):
        if self.reverse:
            if self.current < self.min_ip:
                raise StopIteration
            result = int_to_ip(self.current)
            self.current -= self.step
            return result
        else:
            if self.current > self.max_ip:
                raise StopIteration
            result = int_to_ip(self.current)
            self.current += self.step
            return result

    def next_batch(self, size):
        out = []
        for _ in range(size):
            try:
                out.append(next(self))
            except StopIteration:
                break
        return out

    def contains(self, ip):
        return self.min_ip <= ip_to_int(ip) <= self.max_ip

    @staticmethod
    def to_cidrs(start_ip, end_ip):
        start = ip_to_int(start_ip)
        end = ip_to_int(end_ip)
        out = []
        while start <= end:
            for host_bits in range(32, -1, -1):
                size = 1 << host_bits
                if start % size != 0:
                    continue
                if start + size - 1 > end:
                    continue
                prefix = 32 - host_bits
                out.append(f"{int_to_ip(start)}/{prefix}")
                start += size
                break
        return out
