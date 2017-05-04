<!DOCTYPE html>
<html>
    <head>
        <title>{{ title }}</title>
    </head

    <body>
        <h1>{{ title }}</h1>
        <form method="POST">
            <style scoped="scoped">
                form label::after {
                    content: ':';
                }
            </style>
            <label for="url">URL</label>
            <input id="url" name="url" type="text" />
        </form>
    </body>
</html>
