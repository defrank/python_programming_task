<!DOCTYPE html>
<html>
    <head>
    </head>

    <body>
        <form>
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
