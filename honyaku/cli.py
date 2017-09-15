import click
import hashlib
import polib
import re

from gengo import Gengo


VALID_MSG = re.compile(r'.*[a-zA-Z]+.*')


def identify_entry(entry):
    return hashlib.sha1(entry.msgid.encode('utf-8')).hexdigest()


def is_translatable(entry):
    return entry.msgid and VALID_MSG.match(entry.msgid)


@click.command()
@click.argument('pofile')
@click.argument('source')
@click.argument('target')
@click.option(
    '--tier', default='standard', type=click.Choice(('standard', 'pro')))
@click.option('--public-key', default=None, envvar='GENGO_PUBLIC_KEY')
@click.option('--private-key', default=None, envvar='GENGO_PRIVATE_KEY')
@click.option('--sandbox/--no-sandbox', default=True)
@click.option('--debug/--no-debug', default=False)
def cli(pofile, source, target, tier, public_key, private_key, sandbox, debug):
    """ Takes the given pofile and submits its entries to the gengo API for
    translation. Translated strings are acquired once they are translated
    and stored in the pofile.

    The state of the translations is kept by hasing the strings that should
    be translated. If the strings change the translation won't be matched
    again. As a result you should not change the pofile while the translation
    job is still underway.

    Example:

        honyaku german.po de fr --tier pro

    """

    assert public_key and private_key

    gengo = Gengo(
        public_key=public_key,
        private_key=private_key,
        sandbox=sandbox,
        debug=debug)

    def is_order_complete(order_id):
        order_id = int(order_id)
        order = gengo.getTranslationOrderJobs(id=order_id)['response']['order']
        return len(order['jobs_approved']) == int(order['total_jobs'])

    def fetch_translations(order_id):
        order_id = int(order_id)
        order = gengo.getTranslationOrderJobs(id=order_id)['response']['order']

        results = {}

        for job_id in order['jobs_approved']:
            job = gengo.getTranslationJob(id=int(job_id))['response']['job']
            results[job['slug']] = job['body_tgt']

        return results

    jobs = []

    pofile = polib.pofile(pofile)

    order_id = pofile.metadata.get('gengo-order-id', None)

    if order_id:
        if not is_order_complete(order_id):
            # XXX add the ability to review translations quickly
            print("The file is being translated")
            return
        else:
            translations = fetch_translations(order_id)

            for entry in pofile:
                entry_id = identify_entry(entry)

                if entry_id in translations:
                    entry.msgstr = translations[entry_id]

            del pofile.metadata['gengo-order-id']
            pofile.save()

            return

    for entry in pofile:
        if is_translatable(entry):
            jobs.append({
                'type': 'text',
                'slug': identify_entry(entry),
                'body_src': entry.msgid,
                'lc_src': source,
                'lc_tgt': target,
                'tier': tier,
            })

    result = gengo.postTranslationJobs(jobs={'jobs': {
        'job_{}'.format(ix): job for ix, job in enumerate(jobs)
    }})

    assert result['opstat'] == 'ok', print(result)
    pofile.metadata['gengo-order-id'] = str(result['response']['order_id'])
    pofile.save()
