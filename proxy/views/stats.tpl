<!DOCTYPE html>
<html>
    <head>
        <title>{{ title }}</title>
    </head

    <body>
        <h1>{{ title }}</h1>
        <h2>Statistics</h2>
        <table border="1">
            <thead>
                <tr>
                    <th>Total bytes transferred</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{{ total_bytes_transferred }}</td>
                </tr>
            </tbody>
        </table>
    </body>
</html>
