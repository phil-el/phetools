import sys

def distance(a,b, cost_replace = None):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a, b, n, m = b, a, m, n

    if cost_replace == None:
        cost_replace = {}
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            # obviously this can't handle change ala 'rn' --> 'm'
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            #if add and b[i-1] == u'-':
            #    add = 0.5
            if a[j-1] != b[i-1]:
                delta = 1.0
                if a[j-1] in cost_replace and b[i-1] in cost_replace[a[j-1]]:
                    delta = 0.5
                change += delta
            current[j] = min(add, delete, change)

    return current[n]

if __name__ == "__main__":
	print distance(sys.argv[1], sys.argv[2])
