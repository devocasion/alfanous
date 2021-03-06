# Create your views here.


import json


from collections import OrderedDict as SortedDict
from operator import itemgetter
from random import randint

from django.template import loader
from htmlmin.minify import html_minify

from django.conf import settings
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import render_to_response
from django.views.decorators.gzip import gzip_page
from rest_framework import status
from wui.templatetags.languages import my_get_language_info
from alfanous.Outputs import Raw

# load the search engine, use default paths
RAWoutput = Raw()


def control_access(request):
    """ Controling access to  the API """
    # print request.META["REMOTE_ADDR"]
    # print request.META["REMOTE_HOST"]
    # print request.META["QUERY_STRING"]
    # print request.META["HTTP_REFERER"]
    # print "is ajax?", request.is_ajax()
    return True



@gzip_page
def api(request,action='search'):
    """ JSON Output System II """


    if action not in RAWoutput._domains['action']:
        return HttpResponse('action should be one of: {}'.format(','.join(RAWoutput._domains['action'])), status=status.HTTP_400_BAD_REQUEST)

    control_access(request)
    if request.GET.get('query'):
        response_data = RAWoutput.do(request.GET)
        response = HttpResponse(
            json.dumps(response_data, sort_keys=False),
            content_type="application/json"
        )
        response['charset'] = 'utf-8'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET'
        # response['Content-Encoding'] = 'gzip'
    else:
        response = HttpResponse(
            json.dumps({}, sort_keys=False, indent=4),
            content_type="application/json"
        )
    return response

@gzip_page
def jos2(request): # TODO to be removed
    """ JSON Output System II """
    control_access(request)
    if request.GET.get('query'):
        response_data = RAWoutput.do(request.GET)
        response = HttpResponse(
            json.dumps(response_data, sort_keys=False, indent=4),
            content_type="application/json"
        )
        response['charset'] = 'utf-8'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET'
        # response['Content-Encoding'] = 'gzip'
    else:
        response = HttpResponse(
            json.dumps({}, sort_keys=False, indent=4),
            content_type="application/json"
        )

    return response



@gzip_page
def results(request, unit="aya"):
    if unit not in settings.AVAILABLE_UNITS:
        raise Http404()
    mutable_request = dict(request.GET.items())

    show_params = {"action": "show", "query": "all"}
    if 'query' in mutable_request and mutable_request.get('action', 'search') == 'search':
        search_params = mutable_request
        suggest_params = {"action": "suggest", "query": mutable_request["query"]}
    elif 'search' in mutable_request:
        ## back-compatibility of links:
        # if it's a classic API style, wrap it to the new API style
        search_params = {
            "action": "search",
            "query": mutable_request["search"],
            "page": mutable_request.get('page', 1),
            "sortedby": mutable_request.get('sortedby', 'relevance'),
        }
        suggest_params = {
            "action": "suggest",
            "query": mutable_request["search"],
        }
    else:
        search_params = {}
        suggest_params = {}
        # override the unit flag

    mutable_request["unit"] = unit
    # use search as first action
    raw_search = RAWoutput.do(search_params) if search_params else None
    # use suggest as second action
    raw_suggest = RAWoutput.do(suggest_params) if suggest_params else None
    # use show as third action
    raw_show = RAWoutput.do(show_params) if show_params else None

    # TODO: We shouldn't get the language info here. We have to get the bidi info in the
    # template, same as we do with the other language stuff.

    # language direction  properties
    bidi_val = my_get_language_info(request.LANGUAGE_CODE)['bidi']
    fields_mapping_en_ar = raw_show["show"]["fields_reverse"]
    fields_mapping_en_en = dict([(k, k) for k in fields_mapping_en_ar])

    # a sorted list of translations
    translations = raw_show["show"]["translations"]
    sorted_translations = SortedDict(sorted(translations.iteritems(), key=itemgetter(0)))

    bidi_properties = {
        False: {
            "val": bidi_val,
            "direction": "ltr",
            "align": "left",
            "align_inverse": "right",
            "image_extension": "_en",
            "fields": fields_mapping_en_en
        },
        True: {
            "val": bidi_val,
            "direction": "rtl",
            "align": "right",
            "align_inverse": "left",
            "image_extension": "_ar",
            "fields": fields_mapping_en_ar
        }
    }



    mytemplate = unit + '_search.html'

    context = {
        'current': {
            'path': request.path,
            'request': request.GET.urlencode(),
            'unit': unit,
        },
        "bidi": bidi_properties[bidi_val],
        "available": {
            "units": settings.AVAILABLE_UNITS,
            "translations": sorted_translations
        },
        "params": search_params,
        "results": raw_search,
        "suggestions": raw_suggest,
        "info": raw_show
    }

    template = loader.get_template(mytemplate)

    html = template.render(context, request)

    minified_html = html_minify(html)  # or html_minify(html) as encoding parameter defaults to 'utf-8'


    response = HttpResponse(minified_html)

    if raw_search and (raw_search["error"]["code"] or not raw_search["search"]["interval"]["total"]):
        response.status_code = 404

    return response


@gzip_page
def browse_aya(request, surah, ayah):

    mutable_request = dict(request.GET.items())

    search_params = {
            "action": "search",
            "query": 'sura:"{surah}" + aya_id:{ayah}'.format(surah=surah, ayah=ayah),
            # "view":'full'
    }

    show_params = {"action": "show", "query": "all"}
    raw_search = RAWoutput.do(search_params)
    raw_show = RAWoutput.do(show_params)

    # language direction  properties
    bidi_val = my_get_language_info(request.LANGUAGE_CODE)['bidi']
    fields_mapping_en_ar = raw_show["show"]["fields_reverse"]
    fields_mapping_en_en = dict([(k, k) for k in fields_mapping_en_ar])

    # a sorted list of translations
    translations = raw_show["show"]["translations"]
    sorted_translations = SortedDict(sorted(translations.iteritems(), key=itemgetter(0)))

    bidi_properties = {
        False: {
            "val": bidi_val,
            "direction": "ltr",
            "align": "left",
            "align_inverse": "right",
            "image_extension": "_en",
            "fields": fields_mapping_en_en
        },
        True: {
            "val": bidi_val,
            "direction": "rtl",
            "align": "right",
            "align_inverse": "left",
            "image_extension": "_ar",
            "fields": fields_mapping_en_ar
        }
    }

    mytemplate = 'aya_search.html'

    context = {
        'current': {
            'path': request.path,
            'request': request.GET.urlencode(),
            'unit': 'aya',
        },
        "bidi": bidi_properties[bidi_val],
        "available": {
            "units": settings.AVAILABLE_UNITS,
            "translations": sorted_translations
        },
        "params": search_params,
        "results": raw_search,
        "suggestions": None,
        "info": raw_show
    }

    response = render_to_response(mytemplate, context)
    if raw_search and (raw_search["error"]["code"] or not raw_search["search"]["interval"]["total"]):
        response.status_code = 404

    return response


@gzip_page
def one_aya_page(request, is404=False):
    mutable_request = dict(request.GET.items())
    gid = mutable_request.get('id', -1)
    isRandom = False
    if int(gid) not in xrange(1, 6236 + 1):
        isRandom = True
        gid = randint(1, 6236)
    nb_bg = 4
    bg = mutable_request.get('bg', randint(1, nb_bg))
    if int(bg) not in xrange(1, nb_bg + 1):
        bg = randint(1, nb_bg)
    api = mutable_request.get('api', 0)
    simple = mutable_request.get('simple', 0)
    raw_search = RAWoutput.do({"action": "search", "unit": "aya", "query": "gid:%d" % int(gid)})
    response = HttpResponse(
        json.dumps(raw_search, sort_keys=False, indent=4),
        content_type="application/json"
    )
    raw_search["params"] = {"bg": bg,
                            "gid": gid,
                            "is404": is404,
                            "isRandom": isRandom,
                            "simple": simple
                            }

    new_response = render_to_response('one_aya_page.html', raw_search) if not api else response
    if is404:
        new_response.status_code = 404

    return new_response


@gzip_page
def custom_404(request):
    return one_aya_page(request, is404=True)
