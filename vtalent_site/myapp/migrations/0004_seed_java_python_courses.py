from django.db import migrations


COURSES = [
    {
        'title': 'Java Full Stack Development, AI Integration & AWS Cloud',
        'category': 'Java • Frontend • Backend • AI • Cloud',
        'syllabus': (
            'Frontend Development\n'
            'Core Java and Advanced Java\n'
            'Database Management with MySQL\n'
            'Spring Boot and REST APIs\n'
            'AI Integration in Applications\n'
            'AWS Cloud and Deployment'
        ),
        'display_order': 1,
    },
    {
        'title': 'Python Full Stack Development, AI/ML & AWS Cloud',
        'category': 'Python • Frontend • Django • Machine Learning • Cloud',
        'syllabus': (
            'Frontend Development\n'
            'Core Python and Advanced Python\n'
            'Database Management with MySQL\n'
            'Django and REST APIs\n'
            'Artificial Intelligence and Machine Learning\n'
            'AWS Cloud and Deployment'
        ),
        'display_order': 2,
    },
]


def create_default_courses(apps, schema_editor):
    Course = apps.get_model('myapp', 'Course')
    database = schema_editor.connection.alias

    for course_data in COURSES:
        Course.objects.using(database).get_or_create(
            title=course_data['title'],
            defaults={
                'category': course_data['category'],
                'syllabus': course_data['syllabus'],
                'display_order': course_data['display_order'],
                'is_published': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_adminpasswordresetrequest'),
    ]

    operations = [
        migrations.RunPython(create_default_courses, migrations.RunPython.noop),
    ]
