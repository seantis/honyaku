import click
import functools
import hashlib
import polib
import re
import shutil


VALID_MSG = re.compile(r'.*[a-zA-Z]+.*')


def identify_entry(entry):
    return hashlib.sha1(entry.msgid.encode('utf-8')).hexdigest()


def is_translatable(entry):
    return entry.msgid and VALID_MSG.match(entry.msgid)


def is_translated(entry):
    return entry.msgstr.strip() and True or False


def fits_words_boundary(entry, min_count, max_count):
    min_count = min_count or float('-inf')
    max_count = max_count or float('inf')

    return min_count <= len(entry.msgid.split()) <= max_count


def patch_security_issue():
    # Gengo has been unable to fix a security issue in 2 years, so we fix it
    # ourselves, using a monkey-patch.
    #
    # See https://github.com/gengo/gengo-python/issues/99

    def with_forced_verify(fn):

        @functools.wraps(fn)
        def patched(*args, **kwargs):
            kwargs['verify'] = True
            return fn(*args, **kwargs)

        return patched

    import requests.api
    requests.api.request = with_forced_verify(requests.api.request)


@click.command()
@click.argument('pofile')
@click.argument('source')
@click.argument('target')
@click.option('--tier',
              default='standard', type=click.Choice(('standard', 'pro')))
@click.option('--public-key',
              default=None, envvar='GENGO_PUBLIC_KEY')
@click.option('--private-key',
              default=None, envvar='GENGO_PRIVATE_KEY')
@click.option('--sandbox/--no-sandbox',
              default=False, help="Send requests to the gengo sandbox.")
@click.option('--debug/--no-debug',
              default=False, help="Enables gengo debugging.")
@click.option('--limit',
              default=None, help="Limits the number of jobs.", type=click.INT)
@click.option('--comment',
              default=None, help="Comment to add to all jobs")
@click.option('--tone',
              default=None, help="Tone of the translation")
@click.option('--min-words',
              default=None, type=click.INT,
              help="Minimum number of words in a sentence")
@click.option('--max-words',
              default=None, type=click.INT,
              help="Maximum number of words in sentence")
def cli(pofile, source, target, tier, public_key, private_key, sandbox, debug,
        limit, comment, tone, min_words, max_words):
    """ Takes the given pofile and submits its entries to the gengo API for
    translation. Translated strings are acquired once they are translated
    and stored in the pofile.

    The state of the translations is kept by hashing the strings that should
    be translated. If the strings change the translation won't be matched
    again. As a result you should not change the pofile while the translation
    job is still underway.

    Example:

        honyaku german.po de fr --tier pro

    """

    # to make sure that the security issue is patched properly, we do that
    # before importing Gengo
    patch_security_issue()
    from gengo import Gengo

    assert public_key and private_key

    gengo = Gengo(
        public_key=public_key,
        private_key=private_key,
        sandbox=sandbox,
        debug=debug)

    def fetch_order_jobs(order_id):
        return gengo.getTranslationOrderJobs(id=order_id)['response']['order']

    def is_order_complete(order_id):
        jobs = fetch_order_jobs(order_id)
        return len(jobs['jobs_approved']) == int(jobs['total_jobs'])

    def fetch_translations(order_id):
        jobs = fetch_order_jobs(order_id)

        results = {}

        for job_id in jobs['jobs_approved']:
            job = gengo.getTranslationJob(id=job_id)['response']['job']
            results[job['slug']] = job['body_tgt']

        return results

    jobs = []

    pofile = polib.pofile(pofile)

    order_id = pofile.metadata.get('gengo-order-id', None)

    if order_id:
        if not is_order_complete(order_id):
            reviewable = fetch_order_jobs(order_id)['jobs_reviewable']

            columns = shutil.get_terminal_size((80, 20)).columns
            single_hr = "-" * columns
            double_hr = "=" * columns

            for job_id in reviewable:
                job = gengo.getTranslationJob(id=job_id)['response']['job']
                print(double_hr)
                print(job['body_src'])
                print(single_hr)
                print(job['body_tgt'])
                print(single_hr)

                answer = None
                while answer not in ('a', 'r', 'q'):

                    answer = input(
                        "(a)ccept translation, (r)evise it or (q)uit? ")

                    answer = answer[0]

                if answer == 'q':
                    return

                if answer == 'a':
                    gengo.updateTranslationJob(
                        id=job_id,
                        action={
                            'action': 'approve',
                        }
                    )
                    print("")
                    continue

                if answer == 'r':
                    comment = input("comment for the translator: ")
                    gengo.updateTranslationJob(
                        id=job_id,
                        action={
                            'action': 'revise',
                            'comment': comment
                        }
                    )
                    print("")
                    continue

            if not is_order_complete(order_id):
                print("")
                print("Order is not yet complete")
                return

        translations = fetch_translations(order_id)

        for entry in pofile:
            entry_id = identify_entry(entry)

            if entry_id in translations:
                entry.msgstr = translations[entry_id]

        del pofile.metadata['gengo-order-id']
        pofile.save()

        print("")
        print("Translation has been completed")
        return

    for entry in pofile:
        if is_translatable(entry) and not is_translated(entry):
            if fits_words_boundary(entry, min_words, max_words):
                jobs.append({
                    'type': 'text',
                    'slug': identify_entry(entry),
                    'body_src': entry.msgid,
                    'lc_src': source,
                    'lc_tgt': target,
                    'tier': tier,
                    'comment': comment,
                    'tone': tone,
                })

                if limit and len(jobs) == limit:
                    break

    result = gengo.postTranslationJobs(jobs={'jobs': {
        'job_{}'.format(ix): job for ix, job in enumerate(jobs)
    }})

    assert result['opstat'] == 'ok', print(result)
    pofile.metadata['gengo-order-id'] = str(result['response']['order_id'])
    pofile.save()
